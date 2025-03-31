"""Package for use with HARDWARIO TAPPER"""

import asyncio
import json
import sys
import uuid
from time import sleep, time

import board
import busio
import click
import paho.mqtt.client as mqtt
import uvloop
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
        buzzer_pin: int | str = None,
    ) -> None:
        """Initialize TAPPER."""

        super().__init__(spi, cs_pin)

        self.lock_buzzer = asyncio.Lock()
        self.lock_mqtt = asyncio.Lock()

        self.buzzer: Buzzer = Buzzer(buzzer_pin) if buzzer_pin else Buzzer(18)
        self.buzzer.off()

        self.mqttc = mqtt.Client()
        self.mqttc.connect(mqtt_host, 1883, 60)
        uvloop.run(self.mqtt_publish("device", "alive"))
        logger.debug("MQTT connected")

        self.tamper_switch: Button = (
            Button(tamper_pin, pull_up=False)
            if tamper_pin
            else Button(20, pull_up=False)
        )
        if self.tamper_switch is None:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return True."""
            )

        logger.debug("TAPPER initialized.")

    @property
    @logger.catch()
    def id(self) -> str:
        mac_int = uuid.getnode()
        tapper_id = ":".join(
            f"{(mac_int >> i) & 0xFF:02x}"  # Get one byte, format as 2-digit hex
            for i in reversed(range(0, 48, 8))  # Go over each byte from left to right
        )

        return tapper_id

    @logger.catch()
    async def mqtt_publish(self, topic: str, payload: any) -> None:
        """Publish message to MQTT broker."""

        topic = f"tapper/{self.id}/{topic}"
        logger.debug(f"Publishing MQTT message {topic} {payload}")

        message = json.dumps({"timestamp": time(), "payload": payload})

        await self.lock_mqtt.acquire()
        try:
            self.mqttc.publish(topic, message)
        finally:
            self.lock_mqtt.release()

    @property
    @logger.catch()
    def tamper(self) -> bool:
        """Get state of tamper switch."""

        if self.tamper_switch is not None:
            return self.tamper_switch.is_active
        else:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return False."""
            )
            return True

    @logger.catch()
    async def process_tag(self, uid: bytearray) -> None:
        """Process UID of a detected NFC tag.
        Log tag UID and activate buzzer."""

        logger.debug(f"Processing tag: {' '.join([hex(i) for i in uid])}")

        await self.lock_buzzer.acquire()
        try:
            self.buzzer.on()
            sleep(0.2)
            self.buzzer.off()
            sleep(0.2)
        finally:
            self.lock_buzzer.release()

        await self.mqtt_publish("tag", f"Tag read: {' '.join([hex(i) for i in uid])}")


@logger.catch()
async def tag_loop(tapper: Tapper) -> None:
    while True:
        uid = tapper.read_passive_target(timeout=1)
        if uid is not None:
            logger.debug(f"Tag detected: {' '.join([hex(i) for i in uid])}")
            await tapper.process_tag(uid)

        await asyncio.sleep(1)


@logger.catch()
async def tamper_loop(tapper: Tapper) -> None:
    while True:
        if tapper.tamper:
            await tapper.mqtt_publish("tamper", "Tamper detected!")
            logger.warning(f"Tamper detected: {time()}")

            await tapper.lock_buzzer.acquire()
            try:
                tapper.buzzer.on()
            finally:
                tapper.lock_buzzer.release()

        else:
            await tapper.lock_buzzer.acquire()
            try:
                tapper.buzzer.off()
            finally:
                tapper.lock_buzzer.release()

        await asyncio.sleep(1)


@logger.catch()
async def heartbeat_loop(tapper: Tapper) -> None:
    start = time()
    while True:
        tapper.mqtt_publish(
            "heartbeat", f"TAPPER {tapper.id} Alive! Uptime: {time() - start}"
        )
        await asyncio.sleep(60)


async def loops(tapper: Tapper) -> None:
    await asyncio.gather(tag_loop(tapper), tamper_loop(tapper), heartbeat_loop(tapper))


# Commands
@click.group()
def main() -> None:
    """Define click group"""
    pass


@main.command(help="Display version of TAPPER package.")
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Enable debug mode. (Print debug logs to terminal)",
)
@logger.catch()
def version(debug) -> None:
    """Print the version of the tapper."""

    if debug:
        logger.add(sys.stderr, level="DEBUG", enqueue=True)

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
        logger.add(sys.stderr, level="DEBUG", enqueue=True)

    logger.debug(f"Running TAPPER version {__version__}...")

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # TODO: load from config

    buzzer = 18  # TODO: load from config

    tamper = 20  # TODO: load from config

    tapper = Tapper(spi, cs_pin, mqtt_host, tamper, buzzer)
    ic, ver, rev, support = tapper.firmware_version
    logger.debug("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

    logger.debug("Listening for NFC tags...")

    logger.debug(f"Tamper switch initial state: {tapper.tamper}")

    # TODO: json on MQTT
    # TODO: mqtt topic tapper/{id/MAC}/

    # Run loop
    uvloop.run(loops(tapper))
