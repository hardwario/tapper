import board
import busio
import uvloop
from digitalio import DigitalInOut
from loguru import logger

from tapper.loops import loops
from tapper.tapper import Tapper


def main(mqtt_host, tamper, buzzer):
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # TODO: load from config

    tapper = Tapper(spi, cs_pin, mqtt_host, tamper, buzzer)

    ic, ver, rev, support = tapper.firmware_version
    logger.debug("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

    logger.debug(f"Tamper switch initial state: {tapper.tamper}")

    # Run loop
    uvloop.run(loops(tapper))
