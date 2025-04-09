from time import sleep

import board
import busio
import uvloop
from digitalio import DigitalInOut
from loguru import logger

from tapper.loops import loops
from tapper.tapper import Tapper


@logger.catch()
def main(mqtt_host, tamper, buzzer):
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # TODO: load from config

    tapper = Tapper(spi, cs_pin, mqtt_host, tamper, buzzer)

    ic, ver, rev, support = tapper.firmware_version
    logger.debug(f"Found PN532 with firmware version: {ver}.{rev}")

    logger.debug(f"Tamper switch initial state: {tapper.tamper}")

    # Run loop
    uvloop.run(loops(tapper))


@logger.catch()
async def process_tag(tapper: Tapper, uid: bytearray) -> None:
    """Process UID of a detected NFC tag.
    Log tag UID, activate buzzer and send MQTT message."""

    logger.debug(f"Processing tag: {' '.join([hex(i) for i in uid])}")

    await tapper.lock_buzzer.acquire()
    try:
        tapper.buzzer.on()
        sleep(0.1)
        tapper.buzzer.off()
    finally:
        tapper.lock_buzzer.release()

    await tapper.mqtt_publish("tag", [hex(i) for i in uid])
