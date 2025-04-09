"""The Command Line Interface for TAPPER"""

import json
import sys

import click
from loguru import logger

import tapper.logger
from tapper._version import __version__
from tapper.config import load_config
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
@click.option("-c", "--config", "filepath", help="TAPPER configuration file")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
)
@click.option("-h", "--mqtt", "mqtt_host", help="MQTT host")
@click.option("-lt", "--logtail", "logtail_token", help="Logtail token")
@click.option("-lh", "--logtail_host", "logtail_host", help="Logtail host")
@logger.catch(level="CRITICAL", reraise=True)
def run(debug, mqtt_host, logtail_token, logtail_host, filepath) -> None:
    """Run TAPPER."""
    # TODO: add config file parsing (yaml)

    tapper.logger.start(debug, logtail_token, logtail_host)

    logger.info(f"Running TAPPER version {__version__}")

    if filepath is not None:
        config = load_config(filepath)
        logger.debug("Config loaded: " + json.dumps(config))

        mqtt_host = config["mqtt"]["host"]

        logtail_token = config["logtail"]["token"]
        logtail_host = config["logtail"]["host"]

    buzzer = 18
    tamper = 20

    if mqtt_host is None:
        raise click.UsageError("MQTT host not specified!")

    main(mqtt_host, tamper, buzzer)
