import sys
from time import sleep

import board
import busio
import click
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
        tamper_pin: Button = None,
        buzzer: Buzzer = None,
    ) -> None:
        """Initialize TAPPER."""

        super().__init__(spi, cs_pin)

        self.buzzer: Buzzer = buzzer if buzzer else Buzzer(str(board.D18))
        self.buzzer.off()

        self.tamper_pin: Button = tamper_pin if tamper_pin else Button(str(board.D20))
        if self.tamper_pin is None:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return False."""
            )

        logger.debug("TAPPER initialized.")

    @logger.catch()
    def run(self) -> None:
        """Listen for NFC tags and process.
        Runs an infinite loop that listens for NFC tags.
        """

        logger.debug("Listening for NFC tags...")

        while True:
            uid = self.read_passive_target(timeout=0.5)
            if uid is not None:
                logger.debug(f"Tag detected: {' '.join([hex(i) for i in uid])}")
                self.process_tag(uid)

    @logger.catch()
    def tamper(self) -> bool:
        """Get state of tamper switch."""

        if self.tamper_pin is not None:
            return self.tamper_pin.is_active
        else:
            return False

    @logger.catch()
    def process_tag(self, uid) -> None:
        """Process UID of a detected NFC tag.
        Log tag UID and activate buzzer."""

        logger.debug(f"Processing tag: {' '.join([hex(i) for i in uid])}")
        self.buzzer.on()
        sleep(0.2)
        self.buzzer.off()
        sleep(1.8)
        pass  # TODO: add tag processing logic


@click.group()
def main() -> None:
    """Package for use with HARDWARIO TAPPER"""


@main.command(help="Display version of TAPPER package.")
@logger.catch()
def version() -> None:
    """Print the version of the tapper."""
    click.echo(f"TAPPER version: {click.style(str(__version__), fg='green')}")
    logger.debug(f"TAPPER version: {__version__}")


@main.command(help="Run TAPPER.")
@click.option(
    "--debug", is_flag=True, help="Enable debug mode. (Print debug logs to terminal)"
)
@logger.catch()
def run(debug) -> None:
    """Run TAPPER."""

    if debug:
        logger.add(sys.stderr, level="DEBUG")

    logger.debug(f"Running TAPPER version {__version__}...")

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # TODO: load from config

    buzzer = Buzzer(str(board.D18))  # TODO: load from config

    tamper = Button(str(board.D20))  # TODO: load from config

    tapper = Tapper(spi, cs_pin, tamper, buzzer)
    ic, ver, rev, support = tapper.firmware_version
    logger.debug("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

    tapper.run()
