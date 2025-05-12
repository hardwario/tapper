"""Main logic for TAPPER."""

from time import sleep

import board
import busio
import digitalio
import uvloop
from loguru import logger

import tapper
from tapper import _loops


@logger.catch()
def main(mqtt_host: str, tamper_pin: int, buzzer: int, cs_pin: digitalio.DigitalInOut):
    """Main function for TAPPER."""
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

    tapper_instance: tapper.Tapper = tapper.Tapper(
        spi, cs_pin, mqtt_host, tamper_pin, buzzer
    )

    ic: int
    ver: int
    rev: int
    support: int
    ic, ver, rev, support = tapper_instance.firmware_version
    logger.debug(f"Found PN532 with firmware version: {ver}.{rev}")

    logger.debug(f"Tamper switch initial state: {tapper_instance.get_tamper()}")

    uvloop.run(tapper._loops.loops(tapper_instance))


@logger.catch()
async def process_tag(tapper_instance: tapper.Tapper, uid: bytearray) -> None:
    """Process UID of a detected NFC tag.

    Log tag UID, activate the buzzer, and send MQTT message.
    """
    str_uid = "".join([format(i, "02x").lower() for i in uid])
    logger.debug(f"Processing tag: {''.join([format(i, '02x').lower() for i in uid])}")

    await tapper_instance.lock_buzzer.acquire()
    try:
        tapper_instance.buzzer.on()
        sleep(0.125)
        tapper_instance.buzzer.off()
    finally:
        tapper_instance.lock_buzzer.release()

    await tapper_instance.mqtt_publish(
        "event/tag", {"id": "".join([format(i, "02x").lower() for i in uid])}
    )
