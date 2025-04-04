"""The Command Line Interface for TAPPER"""

import sys

import click
from loguru import logger

import tapper.logger
from tapper._version import __version__
from tapper.main import main


@click.group()
def cli() -> None:
    """Define click group"""
    pass


@cli.command(help="Display version of TAPPER package.")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
)
@logger.catch()
def version(debug) -> None:
    """Print the version of TAPPER."""

    if debug:
        logger.add(sys.stderr, level="DEBUG", enqueue=True)

    click.echo(f"TAPPER version: {click.style(str(__version__), fg='green')}")


@cli.command(help="Run TAPPER.")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
)
@click.option("-h", "--mqtt", "mqtt_host", help="MQTT host", required=True)
@click.option("-lt", "--logtail", "logtail_token", help="Logtail token")
@click.option("-lh", "--logtail_host", "logtail_host", help="Logtail host")
@logger.catch(level="CRITICAL")
def run(debug, mqtt_host, logtail_token, logtail_host) -> None:
    """Run TAPPER."""

    tapper.logger.start(debug, logtail_token, logtail_host)

    logger.info(f"Running TAPPER version {__version__}...")

    buzzer = 18  # TODO: load from config

    tamper = 20  # TODO: load from config

    main(mqtt_host, tamper, buzzer)
