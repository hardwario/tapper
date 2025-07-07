# SPDX-License-Identifier: MIT
"""Define the Tapper class.

This package defines the Tapper class for use with HARDWARIO TAPPER hardware.
It extends the Adafruit PN532 circuit python implementation by Tamper switch, UID of host,
and an internal mqtt client implementation.
"""

import json
import queue
import sys
import threading
import time
import uuid

import busio
import digitalio
import gpiozero
from adafruit_pn532 import spi as pn532
from loguru import logger
from paho.mqtt import client as mqtt


class Tapper(pn532.PN532_SPI):
    """Class for TAPPER.

    Inherits from the PN532_SPI class and adds additional features for TAPPER.
    """

    @logger.catch(reraise=True)
    def __init__(  # noqa: D417
        self,
        spi: busio.SPI,
        cs_pin: digitalio.DigitalInOut,
        tls_options: tuple[str, str, str],
        mqtt_host: str,
        mqtt_port: int = 1883,
        tamper_pin: int = 20,
        buzzer_pin: int = 18,
        led_pins: tuple[int, int, int] = (26, 13, 19),
        relay_pin: int = 14,  # TODO add default for hardware R2.0
    ) -> None:
        """Initialize TAPPER.

        Args:
            spi (): pin for the PN532 SPI device
            cs_pin (): pin for the chip select of the PN532
            tls_options (): paths to the CA certificate file, client certificate, and the client key for use with TLS
            mqtt_host (): ip address of the MQTT broker
            mqtt_port (): port of the MQTT broker
            tamper_pin (): pin of the tamper switch
            buzzer_pin (): pin of the buzzer
            led_pins (): pins of the RGB LED
            relay_pin (): pin of the relay
        """
        super().__init__(spi, cs_pin)

        self.lock_buzzer = threading.Lock()
        self.lock_mqtt = threading.Lock()
        self.lock_nfc = threading.Lock()
        self.lock_led = threading.Lock()
        self.lock_relay = threading.Lock()

        self.buzzer: gpiozero.Buzzer = gpiozero.Buzzer(buzzer_pin)
        self.buzzer.off()

        self._tamper_switch: gpiozero.Button = gpiozero.Button(
            tamper_pin, pull_up=False
        )
        if self._tamper_switch is None:
            logger.warning(
                """Tamper switch not initialized. Tamper will always return True."""
            )

        self.led = gpiozero.RGBLED(led_pins[0], led_pins[1], led_pins[2])

        self.relay = gpiozero.OutputDevice(
            relay_pin, active_high=True, initial_value=False
        )

        logger.info(f"TAPPER {self.get_id()} initialized.")

        self.mqtt_queue: queue.Queue = queue.Queue()

        try:
            self.mqtt_client = mqtt.Client(client_id=self.get_id())
            self.mqtt_client.username = "TAPPER " + self.get_id()
            self.mqtt_client.tls_set(tls_options[0], tls_options[1], tls_options[2])
            self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
        except TimeoutError:
            logger.exception(
                f"MQTT connection timed out, do you have the correct host? Current host: {mqtt_host}",
                level="CRITICAL",
            )
            sys.exit(110)
        except OSError:
            logger.exception(
                f"MQTT connection failed, do you have the correct host? Current host: {mqtt_host}",
                level="CRITICAL",
            )
            sys.exit(113)

        self.mqtt_publish(
            "event/boot",
            {},
        )

        logger.debug("MQTT connected")

    @logger.catch()
    def get_id(self) -> str:
        """Return MAC address.

        Returns:
            str: the uuid of the TAPPER in a human-readable format aa:bb:cc:dd:ee:ff
        """
        mac_int = uuid.getnode()
        tapper_id = ":".join(
            f"{(mac_int >> i) & 0xFF:02x}"  # Get one byte, format as 2-digit hex
            for i in reversed(range(0, 48, 8))  # Go over each byte from left to right
        )

        return tapper_id

    @logger.catch()
    def mqtt_publish(self, topic: str, payload: dict) -> None:
        """Publish a message to TAPPER's MQTT broker.

        Args:
            topic (str): the topic of the MQTT message
            payload (): the payload of the MQTT message
        """
        topic = f"tapper/{self.get_id()}/{topic}"
        logger.trace(f"Publishing MQTT message {topic} {payload}")

        message: str = json.dumps({"timestamp": time.time(), **payload})

        self.lock_mqtt.acquire()
        try:
            self.mqtt_client.publish(topic, message)
        finally:
            self.lock_mqtt.release()

    @logger.catch()
    def get_tamper(self) -> bool:
        """Get state of tamper switch.

        Returns:
            bool: state of tamper switch

        """
        if self._tamper_switch is not None:
            return self._tamper_switch.is_active
        else:
            return True

    @logger.catch()
    def mqtt_schedule(self, topic: str, payload: dict) -> None:
        """Schedule a message to be published via TAPPER's MQTT client."""
        self.mqtt_queue.put((topic, payload))

    @logger.catch()
    def mqtt_publisher_run(self, stop_event: threading.Event) -> None:
        """Run the MQTT publisher."""
        while not stop_event.is_set():
            try:
                topic, payload = self.mqtt_queue.get(timeout=0.1)
                self.mqtt_publish(topic, payload)
                self.mqtt_queue.task_done()
            except queue.Empty:
                pass
