"""OneBot CAI 日志模块"""

import logging
from sys import stdout
from typing import TYPE_CHECKING

import loguru

from .config import config

if TYPE_CHECKING:
    from loguru import Logger

logger: "Logger" = loguru.logger


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
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "onebot_cai.log.LogHandler",
        },
    },
    "loggers": {
        "uvicorn.error": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "INFO",
        },
    },
}
