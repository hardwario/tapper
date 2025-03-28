from loguru import logger
import nfc
import click
from ._version import __version__

# TODO: add config file parsing (yaml)
# TODO: add config file path argument


class Tapper:
    def __init__(self, device="usb"):
        self.device = device.lower()

    @logger.catch
    def listen(self) -> None:
        """Listen for NFC tags."""

        logger.info("Listening...")

        with nfc.ContactlessFrontend(self.device) as clf:
            logger.debug(f"clf: {clf}")

            print(clf)

            tag = clf.connect(
                rdwr={"on-connect": lambda tag: False}
            )  # Waits for tag activation and deactivation, lambda takes in tag and returns False to stop the loop TODO: replace with something useful

            logger.info(f"Tag: {tag}")

            print(tag)


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
@click.option("--device", default="udp", help="NFC device for nfcpy to use.")
@logger.catch()
def run(device) -> None:
    """Run the tapper."""
    logger.debug(f"Running TAPPER version {__version__}...")
    tap = Tapper(device=device)
    tap.listen()
