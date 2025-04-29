"""The Command Line Interface for TAPPER.

This module provides a basic command-line tool for the TAPPER client.
"""

import json
import sys

import board
import click
import digitalio
import yaml
from loguru import logger

from tapper import _logger as tapper_logger
from tapper import _main as tapper_main
from tapper import _version as tapper_version


@click.group()
def _cli() -> None:
    """Define a click group."""
    pass


@_cli.command(name="version", help="Display version of TAPPER package.")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
)
@logger.catch()
def _version(debug: bool) -> None:
    """Print the version of TAPPER.

    Args:
        debug (bool): enable debug mode - print debug logs to terminal
    """
    if debug:
        logger.add(sys.stderr, level="DEBUG", enqueue=True)

    click.echo(
        f"TAPPER version: {click.style(str(tapper_version.__version__), fg='green')}"
    )


@_cli.command(name="run", help="Run TAPPER.")
@click.option("-c", "--config", "path", help="Path to theTAPPER configuration file")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode - print debug logs to terminal",
)
@click.option("-h", "--mqtt", "mqtt_host", help="MQTT host")
@click.option("-lt", "--logtail", "logtail_token", help="Logtail token")
@click.option("-lh", "--logtail_host", "logtail_host", help="Logtail host")
@logger.catch(level="CRITICAL", reraise=True)
def _run(
    debug: bool, mqtt_host: str, logtail_token: str, logtail_host: str, path: str
) -> None:
    """Run TAPPER.

    Args:
        debug (bool): enable debug mode - print debug logs to terminal
        mqtt_host (str): address of MQTT broker
        logtail_token (str): token for logtail
        logtail_host (str): host for logtail
        path (str): path to the TAPPER configuration file
    """
    if path is not None:
        with open(path, "r") as file:
            config: dict = yaml.safe_load(file)

        mqtt_host: str = config["mqtt"]["host"]

        logtail_token: str = config["logtail"]["token"]
        logtail_host: str = config["logtail"]["host"]

        tapper_logger.logger_start(debug, logtail_token, logtail_host)

        logger.debug("Config loaded: " + f"'{json.dumps(config)}'")

    else:
        tapper_logger.logger_start(debug, logtail_token, logtail_host)

    logger.info(f"Running TAPPER version {tapper_version.__version__}")

    buzzer_pin: int = 18
    tamper_pin: int = 20
    cs_pin: digitalio.DigitalInOut = digitalio.DigitalInOut(board.D8)

    if mqtt_host is None:
        raise click.UsageError("MQTT host not specified!")

    tapper_main.main(mqtt_host, tamper_pin, buzzer_pin, cs_pin)
