"""Main logic for TAPPER."""

import queue
from time import sleep

import board
import busio
import digitalio
from loguru import logger

import tapper
from tapper import _outputs as tapper_outputs
from tapper import _threads as tapper_threads


@logger.catch()
def main(
    mqtt_host: str,
    tamper_pin: int,
    buzzer_pin: int,
    cs_pin: digitalio.DigitalInOut,
    led_pins: tuple[int, int, int],
):
    """Main function for TAPPER."""
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

    tapper_instance: tapper.Tapper = tapper.Tapper(
        spi, cs_pin, mqtt_host, tamper_pin, buzzer_pin, led_pins
    )

    tapper_instance.mqtt_queue = queue.Queue()

    ic: int
    ver: int
    rev: int
    support: int
    ic, ver, rev, support = tapper_instance.firmware_version
    logger.debug(f"Found PN532 with firmware version: {ver}.{rev}")

    logger.debug(f"Tamper switch initial state: {tapper_instance.get_tamper()}")

    tapper_instance.request_queue = queue.Queue()

    tapper_instance.mqtt_client.subscribe(
        f"tapper/{tapper_instance.get_id()}/control/request"
    )

    logger.debug(f"Subscribed to: tapper/{tapper_instance.get_id()}/control/request")

    tapper_instance.mqtt_client.user_data_set(
        {"tapper": tapper_instance, "requests": tapper_instance.request_queue}
    )

    logger.debug(
        f"MQTT client user data set: {tapper_instance.mqtt_client.user_data_get()}"
    )

    tapper_instance.mqtt_client.on_message = tapper_outputs.add_to_request_queue

    tapper_threads.start_threads(tapper_instance)


@logger.catch()
def process_tag(tapper_instance: tapper.Tapper, uid: bytearray) -> None:
    """Process UID of a detected NFC tag.

    Log tag UID, activate the buzzer, and send MQTT message.
    """
    logger.debug(f"Processing tag: {''.join([format(i, '02x').lower() for i in uid])}")

    tapper_instance.lock_buzzer.acquire()
    tapper_instance.lock_led.acquire()

    try:
        tapper_instance.led.color = (1, 1, 0)
        tapper_instance.buzzer.on()
        sleep(0.125)
        tapper_instance.led.off()
        tapper_instance.buzzer.off()
    finally:
        tapper_instance.lock_buzzer.release()
        tapper_instance.lock_led.release()

    tapper_instance.mqtt_schedule(
        "event/tag", {"id": "".join([format(i, "02x").lower() for i in uid])}
    )

    logger.debug("Tag processing finished")
