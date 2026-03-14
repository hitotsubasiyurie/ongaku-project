import time
import asyncio
import threading
from typing import Any

import requests
from cloakbrowser import launch_async
from patchright.async_api import Browser, BrowserContext, Route

from src.core.cache import g_request_cache, full_name, make_key
from src.utils import retry, RateLimiter
from src.core.logger import logger


class RequestScraper:

    # 请求 间隔 1.5 秒
    _REQUEST_INTERVAL = 1.5
    # 请求 超时 8 秒
    _REQUEST_TIMEOUT = 8
    # 请求 重试 10 次
    _REQUEST_RETRY_TIMES = 10
    # 请求 重试间隔 5 秒
    _REQUEST_RETRY_DELAY = 5
    # 请求 请求头
    _REQUEST_HEADERS = None

    def __init__(self) -> None:
        # 请求 速率限制器
        self.__rate_limiter = RateLimiter(self._REQUEST_INTERVAL)
        # 封装 request.get 方法
        self.__request_get = retry(self._REQUEST_RETRY_TIMES, self._REQUEST_RETRY_DELAY)(self.__rate_limiter(requests.get))

    def _scraper_get(self, url: str, use_cache: bool = True, **kwargs) -> requests.Response:
        """
        Scraper 网络请求。

        :param use_cache: 是否使用缓存
        """
        key = make_key(full_name(self.__request_get), url)
        result = g_request_cache.get(key) if use_cache else None
        if result is None:
            if "timeout" not in kwargs: kwargs["timeout"] = self._REQUEST_TIMEOUT
            if "headers" not in kwargs: kwargs["headers"] = self._REQUEST_HEADERS
            result = self.__request_get(url, **kwargs)
            g_request_cache.set(key, result)

        return result


class BrowserScraper:

    # 请求 间隔 1.5 秒
    _REQUEST_INTERVAL = 1.5
    # 最大打开页面数
    _MAX_PAGE_NUM = 10
    # 拦截的资源类型
    _ABORTED_RESOURCE_TYPES = {"image", "font", "media"}
    # 页面打开次数后 重启浏览器
    _RESTART_THRESHOLD = 1000
    # cookies
    _COOKIES = []

    def __init__(self) -> None:
        # 请求 速率限制器
        self.__rate_limiter = RateLimiter(self._REQUEST_INTERVAL)
        # asyncio 事件循环
        self.__event_loop = asyncio.new_event_loop()
        # 打开页面数 信号量
        self._page_semaphore: asyncio.Semaphore
        # 重启浏览器 计数器
        self.__restart_counter = 0
        # 重启浏览器 锁
        self.__restart_lock: asyncio.Lock
        # 浏览器 user agent
        self.__user_agent: str = ""

        def __thread_run_loop() -> None:
            # 子线程运行 loop
            asyncio.set_event_loop(self.__event_loop)
            # 初始化 同步原语
            self.__restart_lock = asyncio.Lock()
            self._page_semaphore = asyncio.Semaphore(self._MAX_PAGE_NUM)
            self.__event_loop.run_forever()

        threading.Thread(target=__thread_run_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.__setup_browser(), self.__event_loop).result()

    async def __setup_browser(self) -> None:
        """
        配置浏览器。
        """
        self._browser: Browser = await launch_async(headless=False)
        self._context: BrowserContext = await self._browser.new_context()

        await self._context.route("**/*", self.__route_handler)
        if self._COOKIES:
            await self._context.add_cookies(self._COOKIES)

    def close(self) -> None:
        """
        关闭 Scraper。
        """
        if not self.__event_loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._browser.close(), self.__event_loop).result()
        finally:
            self.__event_loop.call_soon_threadsafe(self.__event_loop.stop)

    def _get_request_cookies(self, url: str) -> tuple:
        """
        获取网络请求参数。

        :returns headers, cookies: 
        """
        headers = {"User-Agent": self.__user_agent}

        browser_cookies = asyncio.run_coroutine_threadsafe(self._context.cookies(url), self.__event_loop).result()
        cookies = {c["name"]: c["value"] for c in browser_cookies}

        return headers, cookies

    def _scraper_get(self, url: str, wait_selector: str = "", use_cache: bool = True) -> requests.Response:
        """
        Scraper 网络请求。

        :param wait_selector: 需要等待出现的元素
        :param use_cache: 是否使用缓存
        """
        func_name = full_name(self.__sync_browser_get)
        key = make_key(func_name, url, wait_selector)
        resp = g_request_cache.get(key) if use_cache else None
        if resp is None:
            resp = requests.Response()
            text = self.__rate_limiter(self.__sync_browser_get)(url, wait_selector)
            resp._content = text.encode()
            g_request_cache.set(key, resp)
        return resp

    def __sync_browser_get(self, url: str, wait_selector: str) -> str:
        future = asyncio.run_coroutine_threadsafe(
            self.__async_browser_get(url, wait_selector), 
            self.__event_loop
        )
        return future.result()

    async def __async_browser_get(self, url: str, wait_selector: str) -> str:
        # 检查 重启计数器
        async with self.__restart_lock:
            self.__restart_counter += 1
            if self.__restart_counter >= self._RESTART_THRESHOLD:
                self.__restart_counter = 0
                await self.__restart_browser()

        async with self._page_semaphore:
            page = await self._context.new_page()
            # 保存 ua
            if not self.__user_agent:
                self.__user_agent = await page.evaluate("navigator.userAgent")
            try:
                await page.goto(url, wait_until="domcontentloaded")
                # 永远等待
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=0)
                return await page.content()
            finally:
                await page.close()

    async def __route_handler(self, route: Route) -> Any:
        """
        浏览器 路由规则。
        """
        # 放行 cloudflare
        clooudflare_keys = ("challenges.cloudflare.com", "/cdn-cgi", "static.cloudflareinsights.com")
        if any(k in route.request.url for k in clooudflare_keys):
            await route.continue_()
        elif route.request.resource_type in self._ABORTED_RESOURCE_TYPES:
            await route.abort()
        else:
            await route.continue_()

    async def __restart_browser(self) -> None:
        """
        重启浏览器。
        """
        logger.info("Reached restart thresshold. Wait to restart browser.")
        # 等待所有页面关闭
        while self._page_semaphore._value < self._MAX_PAGE_NUM:
            await asyncio.sleep(1)
        await self._browser.close()
        await self.__setup_browser()
        logger.info("Restart browser.")



