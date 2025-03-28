from loguru import logger

logger.remove()
logger.add(
    "~/.tapper/logs/tapper_{time}.log",
    rotation="1 day",
    retention=3,
    level="TRACE",
)
