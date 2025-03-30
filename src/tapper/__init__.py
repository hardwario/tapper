import os

from loguru import logger

if not os.path.exists(os.path.join("~", ".tapper", "logs")):
    os.makedirs(os.path.join("~", ".tapper", "logs"), exist_ok=True)

homedir = os.path.expanduser("~")

logger.remove()
logger.add(
    os.path.join(homedir, ".tapper/logs/tapper_{time}.log"),
    rotation="1 day",
    retention="3 days",
    level="TRACE",
)
