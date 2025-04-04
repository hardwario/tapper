import os

from loguru import logger

homedir = os.path.expanduser("~")

if not os.path.exists(os.path.join(homedir, ".tapper/logs/tapper_{time}.log")):
    os.makedirs(os.path.join(homedir, ".tapper/logs/tapper_{time}.log"), exist_ok=True)

logger.remove()
logger.add(
    os.path.join(homedir, ".tapper/logs/tapper_{time}.log"),
    rotation="1 day",
    retention="3 days",
    level="TRACE",
    enqueue=True,
    serialize=True,
    backtrace=True,
    delay=True,
)
