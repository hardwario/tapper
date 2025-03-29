from loguru import logger
import click
from ._version import __version__
import sys
from adafruit_pn532.spi import PN532_SPI
import busio
from digitalio import DigitalInOut
import board

# TODO: add config file parsing (yaml)
# TODO: add config file path argument


class Tapper(PN532_SPI):
    """Class for TAPPER.
    Inherits from PN532_SPI class.
    Adds additional functionality for TAPPER."""

    @logger.catch()
    def __init__(self, spi: busio.SPI, cs_pin: DigitalInOut) -> None:
        """Initialize TAPPER."""
        super().__init__(spi, cs_pin)
        logger.debug("TAPPER initialized.")

    @logger.catch()
    def process_tag(self, uid: bytearray) -> None:
        """Process UID of a detected NFC tag."""
        logger.debug(f"TAPPER processing tag. {[hex(i) for i in uid]}")
        pass

    @logger.catch()
    def run(self) -> None:
        """Listen for NFC tags and process.
        Runs an infinite loop that listens for NFC tags.
        """
        logger.debug("Listening for NFC tags...")
        while True:
            uid = self.read_passive_target(timeout=0.5)
            if uid is not None:
                logger.info(f"Tag detected: {[hex(i) for i in uid]}")
                self.process_tag(uid)


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

    # SPI connection:
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)
    tapper = Tapper(spi, cs_pin)
    tapper.run()  # TODO: add on_connect function
