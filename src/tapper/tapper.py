"""Package for use with HARDWARIO TAPPER"""

import sys
from time import sleep

import board
import busio
import click
import paho.mqtt.client as mqtt
from adafruit_pn532.spi import PN532_SPI
from digitalio import DigitalInOut
from gpiozero import Button, Buzzer
from loguru import logger

from tapper._version import __version__

# TODO: add config file parsing (yaml)
# TODO: add config file path argument
# TODO: Send MQTT events on tag detection
# TODO: add tamper detection


class Tapper(PN532_SPI):
    """Class for TAPPER.
    Inherits from PN532_SPI class.
    Adds additional functionality for TAPPER."""

    @logger.catch()
    def __init__(
        self,
        spi: busio.SPI,
        cs_pin: DigitalInOut,
        mqtt_host: str,
        tamper_pin: int | str = None,
        buzzer: int | str = None,
    ) -> None:
        """Initialize TAPPER."""

        super().__init__(spi, cs_pin)

        self.buzzer: Buzzer = Buzzer(buzzer) if buzzer else Buzzer(18)
        self.buzzer.off()

        self.mqttc = mqtt.Client()
        self.mqttc.connect(mqtt_host, 1883, 60)
        self.mqttc.publish("tapper/device", "TAPPER Alive")
        logger.debug("MQTT connected")

        self.tamper_switch: Button = (
            Button(tamper_pin, pull_up=False)
            if tamper_pin
            else Button(20, pull_up=False)
        )
        if self.tamper_switch is None:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return False."""
            )

        logger.debug("TAPPER initialized.")

    @logger.catch()
    def tamper(self) -> bool:
        """Get state of tamper switch."""

        if self.tamper_switch is not None:
            return self.tamper_switch.is_active
        else:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return False."""
            )
            return False

    @logger.catch()
    def process_tag(self, uid: bytearray) -> None:
        """Process UID of a detected NFC tag.
        Log tag UID and activate buzzer."""

        logger.debug(f"Processing tag: {' '.join([hex(i) for i in uid])}")

        self.buzzer.on()
        sleep(0.2)
        self.buzzer.off()
        sleep(1.8)

        self.mqttc.publish("tapper/tag", f"Tag read: {' '.join([hex(i) for i in uid])}")


@click.group()
def main() -> None:
    """Define click group"""
    pass


@main.command(help="Display version of TAPPER package.")
@logger.catch()
def version() -> None:
    """Print the version of the tapper."""
    click.echo(f"TAPPER version: {click.style(str(__version__), fg='green')}")
    logger.debug(f"TAPPER version: {__version__}")


@main.command(help="Run TAPPER.")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
)
@click.option("--mqtt", "mqtt_host", help="MQTT host", required=True)
@logger.catch()
def run(debug, mqtt_host) -> None:
    """Run TAPPER."""

    if debug:
        logger.add(sys.stderr, level="DEBUG")

    logger.debug(f"Running TAPPER version {__version__}...")

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # TODO: load from config

    buzzer = 18  # TODO: load from config

    tamper = 20  # TODO: load from config

    tapper = Tapper(spi, cs_pin, mqtt_host, tamper, buzzer)
    ic, ver, rev, support = tapper.firmware_version
    logger.debug("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

    logger.debug("Listening for NFC tags...")

    tamper_init = tapper.tamper()
    logger.debug(f"Tamper switch initial state: {tamper_init}")

    # Run loop
    while True:
        uid = tapper.read_passive_target(timeout=0.5)
        if uid is not None:
            logger.debug(f"Tag detected: {' '.join([hex(i) for i in uid])}")
            tapper.process_tag(uid)

        # Debug
        if tapper.tamper():
            logger.debug("Tamper switch active.")
        else:
            logger.debug("Tamper switch not active.")

        if tamper_init != tapper.tamper():
            logger.warning("Tampering detected!")
            tapper.mqttc.publish("tapper/tamper", "Tampering detected!")
            tapper.buzzer.on()
        else:
            tapper.buzzer.off()
