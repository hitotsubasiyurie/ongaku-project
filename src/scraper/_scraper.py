import asyncio
import threading
from typing import Any

import requests
from cloakbrowser import launch_async
from patchright.async_api import Browser, BrowserContext, Route, Page

from src.core.cache import g_request_cache, full_name, make_key
from src.utils import retry, RateLimiter


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
        self.__rate_limiter = RateLimiter(self._REQUEST_INTERVAL)
        self.__request_get = retry(self._REQUEST_RETRY_TIMES, self._REQUEST_RETRY_DELAY)(self.__rate_limiter(requests.get))

    def _scraper_get(self, url: str, **kwargs) -> requests.Response:
        func_name = full_name(self.__request_get)
        key = make_key(func_name, url, kwargs)
        result = g_request_cache.get(key)
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
    _ABORTED_RESOURCE_TYPES = {"image",}
    # cookies
    _COOKIES = []

    def __init__(self) -> None:
        self.__rate_limiter = RateLimiter(self._REQUEST_INTERVAL)
        self.__event_loop = asyncio.new_event_loop()
        threading.Thread(target=self.__thread_run_loop, args=(self.__event_loop,), daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.__setup(), self.__event_loop).result()

    def __thread_run_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def __setup(self) -> None:
        self._browser: Browser = await launch_async(headless=False)
        self._context: BrowserContext = await self._browser.new_context()
        self._semaphore = asyncio.Semaphore(self._MAX_PAGE_NUM)

        await self._context.route("**/*", self.__route_handler)
        if self._COOKIES:
            await self._context.add_cookies(self._COOKIES)

    def close(self) -> None:
        if not self.__event_loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._browser.close(), self.__event_loop).result()
        finally:
            self.__event_loop.call_soon_threadsafe(self.__event_loop.stop)

    def _scraper_get(self, url: str, wait_selector: str = "") -> requests.Response:
        """
        :param wait_selector: 需要等待出现的元素
        """
        func_name = full_name(self.__sync_browser_get)
        key = make_key(func_name, url, wait_selector)
        resp = g_request_cache.get(key)
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
        async with self._semaphore:
            page = await self._context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded")
                # 永远等待
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=0)
                return await page.content()
            finally:
                await page.close()

    async def __route_handler(self, route: Route) -> Any:
        # 放行 cloudflare
        clooudflare_keys = ("challenges.cloudflare.com", "/cdn-cgi", "static.cloudflareinsights.com")
        if any(k in route.request.url for k in clooudflare_keys):
            await route.continue_()
        elif route.request.resource_type in self._ABORTED_RESOURCE_TYPES:
            await route.abort()
        else:
            await route.continue_()
