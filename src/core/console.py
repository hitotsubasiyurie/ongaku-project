import json
import sys
from pathlib import Path
from typing import TypeVar, Any, Type, Protocol

from src.core.logger import logger, WithRawFormatter

################################################################################
### 协议
################################################################################


_T_contra = TypeVar("_T_contra", contravariant=True)
_T_co = TypeVar("_T_co", covariant=True)


class SupportsNoArgReadline(Protocol[_T_co]):
    def readline(self) -> _T_co: ...


class SupportsWriteAndFlush(Protocol[_T_contra]):
    def write(self, s: _T_contra, /) -> object: ...
    def flush(self) -> object: ...

################################################################################
### 控制台
################################################################################

g_stdin = sys.stdin
# 默认混合输出
g_stdout = sys.stdout
g_stderr = sys.stdout


def set_output(stdout: SupportsWriteAndFlush[str], stderr: SupportsWriteAndFlush[str]) -> None:
    global g_stdout, g_stderr
    g_stdout = stdout
    g_stderr = stderr


def set_input(stdin: SupportsNoArgReadline[str]) -> None:
    global g_stdin
    g_stdin = stdin


def cprint(obj: object, end: str | None = "\n") -> None:
    """
    自定义 print 函数。

    1. 非字符串对象序列化为 json 格式
    2. 在打印前将内容原样写入日志
    3. 打印至 g_stdout
    """
    s = obj if isinstance(obj, str) else json.dumps(obj, indent=4, ensure_ascii=False)
    logger.debug(s, extra={WithRawFormatter.IN_RAW_KEY: True})
    print(s, end=end, file=g_stdout)


def cinput(prompt: str = "") -> str:
    """
    自定义 input 函数。

    1. 从 g_stdin 读取行输入
    2. 将提示和输入原样写入日志
    """
    prompt and cprint(prompt, end="")
    s = g_stdin.readline().rstrip("\n")
    logger.debug(s + "\n", extra={WithRawFormatter.IN_RAW_KEY: True})
    return s


_T = TypeVar("T")


def easy_cinput(prompt: str = "", default: Any = None, return_type: Type[_T] = str) -> _T:
    """
    :param default: 默认为 None 时，会循环提示输入
    :param return_type: 返回结果类型
    """

    if default is not None and not isinstance(default, return_type):
        raise TypeError(f"Default value invalid. Expecting type {return_type.__name__}")

    while True:
        val = cinput(prompt + "\n" + (f"({default})" if default is not None else "") +"?: ")
        if not val:
            if default is None:
                continue
            return default
        else:
            try:
                if return_type == Path:
                    val = Path(val.strip().strip("'\""))
                else:
                    val = return_type(val)
                return val
            except Exception:
                continue







