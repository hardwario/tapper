r"""HARDWARIO TAPPER package.

A package for use with HARDWARIO TAPPER hardware.
It extends the Adafruit PN532 circuit python implementation by Tamper switch, UID of host,
and an internal mqtt client implementation.

Typical usage example:

    session = tapper.Tapper()
    uid = session.read_passive_target(timeout=0.5)
    session.mqtt_publish("topic", "payload")
    id = session.id
    tamper_state = session.get_tamper()


"""

import os

from loguru import logger

from tapper.tapper import Tapper

homedir: str = os.path.expanduser("~")

if not os.path.exists(os.path.join(homedir, ".tapper/logs/tapper_{time}.log")):
    os.makedirs(os.path.join(homedir, ".tapper/logs/tapper_{time}.log"), exist_ok=True)

logger.remove()
logger.add(
    os.path.join(homedir, ".tapper/logs/tapper_{time}.log"),
    rotation="1 day",
    retention=3,
    level="TRACE",
    enqueue=True,
    serialize=True,
    backtrace=True,
    delay=True,
    colorize=True,
)
