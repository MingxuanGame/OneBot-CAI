"""OneBot CAI 日志模块"""
import logging
from sys import stdout
from typing import TYPE_CHECKING, Any

import loguru
from hypercorn.logging import Logger as HypercornLogger

from .config import config

if TYPE_CHECKING:
    from loguru import Logger as LoguruLogger
    from hypercorn.typing import WWWScope, ResponseSummary

logger: "LoguruLogger" = loguru.logger


# Code from NoneBot2
# https://github.com/nonebot/nonebot2/blob/master/nonebot/log.py
class LogHandler(logging.Handler):  # pragma: no cover
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# logger
LOG_LEVEL = config.universal.log_level or 20
logger.remove()
logger.add(
    stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> [<level>{level}</level>] "
    "<cyan>{name}</cyan> | {message}",
    level=LOG_LEVEL,
)

for log_name in ("apscheduler", "cai", "httpx", "fastapi"):
    log_level = 30 if log_name == "apscheduler" else LOG_LEVEL
    logging_logger = logging.getLogger(log_name)
    logging_logger.setLevel(log_level)
    logging_logger.handlers.clear()
    logging_logger.addHandler(LogHandler())


class HypercornLoguruLogger(HypercornLogger):
    async def access(
        self,
        request: "WWWScope",
        response: "ResponseSummary",
        request_time: float,
    ) -> None:
        logger.info(
            self.access_log_format
            % (self.atoms(request, response, request_time))
        )

    async def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.critical(message, *args, **kwargs)

    async def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.error(message, *args, **kwargs)

    async def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.warning(message, *args, **kwargs)

    async def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.info(message, *args, **kwargs)

    async def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.debug(message, *args, **kwargs)

    async def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        logger.exception(message, *args, **kwargs)

    async def log(
        self, level: int, message: str, *args: Any, **kwargs: Any
    ) -> None:
        logger.log(level, message, *args, **kwargs)
