"""The Command Line Interface for TAPPER.

This module provides a basic command-line tool for the TAPPER client.
"""

import json

import board
import click
import digitalio
import yaml
from loguru import logger

from tapper import _config as tapper_config
from tapper import _logger as tapper_logger
from tapper import _main as tapper_main
from tapper import _version as tapper_version


@click.group(help="The TAPPER Client CLI")
def cli() -> None:
    """Define a click group."""
    pass


@cli.command(name="version", help="Display version of TAPPER package.")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
    hidden=True,
)
@logger.catch()
def _version(debug: bool) -> None:
    """Print the version of TAPPER.

    Args:
        debug (bool): enable debug mode - print debug logs to terminal
    """
    tapper_logger.logger_start(debug)

    click.echo(
        f"TAPPER version: {click.style(str(tapper_version.__version__), fg='green')}"
    )


@cli.command(name="run", help="Run TAPPER.")
@click.option("-c", "--config", "path", help="Path to the TAPPER configuration file")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode - print debug logs to terminal",
    hidden=True,
)
@click.option("-h", "--mqtt", "mqtt_host", help="MQTT broker host")
@click.option("-p", "--port", "mqtt_port", default=1883, help="MQTT broker port")
@click.option("-ca", "--cafile", "tls_ca", help="Path to the CA certificate file")
@click.option(
    "-cert",
    "--certfile",
    "tls_cert",
    help="Path to the client certificate file for use with TLS",
)
@click.option(
    "-key", "--keyfile", "tls_key", help="Path to the key file for use with TLS"
)
@click.option("--legacy", "legacy", is_flag=True, help="Run with legacy r1.0 hardware")
@logger.catch(level="CRITICAL", reraise=True)
def _run(
    debug: bool,
    mqtt_host: str,
    mqtt_port: int,
    path: str,
    legacy: bool,
    tls_ca: str,
    tls_cert: str,
    tls_key: str,
) -> None:
    """Run TAPPER.

    Args:
        debug (bool): enable debug mode - print debug logs to terminal
        mqtt_host (str): ip address of the MQTT broker
        mqtt_port (int): port of the MQTT broker
        tls_ca (): path to the CA certificate file
        tls_cert (): path to the client TLS certificate
        tls_key (): path to the TLS client key
        path (str): path to the TAPPER configuration file
        legacy (bool): run with legacy r1.0 hardware

    Raises:
        click.UsageError: something wasn't specified or was specified improperly
    """
    tapper_logger.logger_start(debug)

    if path is not None:
        mqtt_host, mqtt_port, tls_ca, tls_cert, tls_key, legacy = tapper_config.load(
            path
        )

    logger.debug(
        f"Config loaded: {mqtt_host}:{mqtt_port}, CA: {tls_ca}, Certificate: {tls_cert}, Key: {tls_key}"
    )

    logger.info(f"Running TAPPER version {tapper_version.__version__}")

    if legacy:
        buzzer_pin: int = 18
        tamper_pin: int = 20
        led_pins: tuple[int, int, int] = (17, 16, 15)
    else:
        buzzer_pin: int = 21
        tamper_pin: int = 6
        led_pins: tuple[int, int, int] = (26, 13, 19)

    cs_pin: digitalio.DigitalInOut = digitalio.DigitalInOut(board.D8)

    if mqtt_host is None:
        raise click.UsageError("MQTT host not specified!")

    tapper_main.main(
        mqtt_host,
        mqtt_port,
        tamper_pin,
        buzzer_pin,
        cs_pin,
        led_pins,
        (tls_ca, tls_cert, tls_key),
    )
