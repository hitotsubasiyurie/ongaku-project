import logging
import sys
from pathlib import Path


class PrintLogger:
    """拦截 print，写入文件，同时仍然打印到控制台"""
    def __init__(self, logfile: Path):
        self.terminal = sys.__stdout__
        self.logfile = open(logfile, "a", encoding="utf-8")

    def write(self, message):
        # 控制台原样输出
        self.terminal.write(message)
        self.terminal.flush()
        # 写入文件（不加时间戳/格式化）
        self.logfile.write(message)
        self.logfile.flush()

    def flush(self):
        self.terminal.flush()
        self.logfile.flush()


def setup_logger(logfile: Path, level=logging.INFO) -> logging.Logger:
    logfile.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("cli_tool")
    logger.setLevel(level)

    # 日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台输出 logger
    ch = logging.StreamHandler(sys.__stdout__)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 文件输出 logger
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # 拦截 print
    sys.stdout = PrintLogger(logfile)

    return logger


if __name__ == "__main__":
    log_file = Path("logs/app.log")
    logger = setup_logger(log_file)

    logger.info("程序启动")
    print("这是 print 输出（无时间戳）")
    logger.warning("这是 logger 输出（带时间戳）")
    print("程序结束")
