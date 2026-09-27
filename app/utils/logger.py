import sys

from loguru import logger

logger.remove()

if sys.stdout is not None:
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:HH:mm:ss} | {level} | {message}"
    )

__all__ = ["logger"]