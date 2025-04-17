"""Package for use with HARDWARIO TAPPER"""

import asyncio
import json
import uuid
from time import sleep, time

import busio
import paho.mqtt.client as mqtt
import uvloop
from adafruit_pn532.spi import PN532_SPI
from digitalio import DigitalInOut
from gpiozero import Button, Buzzer
from loguru import logger


class Tapper(PN532_SPI):
    """Class for TAPPER.
    Inherits from PN532_SPI class.
    Adds additional functionality for TAPPER."""

    @logger.catch(reraise=True)
    def __init__(
        self,
        spi: busio.SPI,
        cs_pin: DigitalInOut,
        mqtt_host: str,
        tamper_pin: int | str = 20,
        buzzer_pin: int | str = 18,
    ) -> None:
        """Initialize TAPPER."""

        super().__init__(spi, cs_pin)

        self.lock_buzzer = asyncio.Lock()
        self.lock_mqtt = asyncio.Lock()
        self.lock_nfc = asyncio.Lock()

        self.buzzer: Buzzer = Buzzer(buzzer_pin)
        self.buzzer.off()

        try:
            self.mqtt_client = mqtt.Client(client_id="TAPPER" + self.id)
            self.mqtt_client.connect(mqtt_host, 1883, 60)
        except TimeoutError:
            logger.exception(
                "MQTT connection timed out, do you have the correct host?",
                level="CRITICAL",
            )
            sleep(2)  # Let logtail finish
            quit(113)

        uvloop.run(self.mqtt_publish("device", "alive"))
        logger.debug("MQTT connected")

        self.tamper_switch: Button = Button(tamper_pin, pull_up=False)
        if self.tamper_switch is None:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return True."""
            )

        logger.info(f"TAPPER {self.id} initialized.")

    @property
    @logger.catch()
    def id(self) -> str:
        """Return MAC address."""

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
            self.mqtt_client.publish(topic, message)
        finally:
            self.lock_mqtt.release()

    @property
    @logger.catch()
    def tamper(self) -> bool:
        """Get state of tamper switch."""

        if self.tamper_switch is not None:
            return self.tamper_switch.is_active
        else:
            return True
