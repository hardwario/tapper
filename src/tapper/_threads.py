import json
import signal
import threading
import time

import psutil
from loguru import logger

import tapper
from tapper import _main as main


@logger.catch()
def _tag_thread(tapper_instance: tapper.Tapper, stop_event: threading.Event) -> None:
    """Thread for reading NFC Tags."""
    while not stop_event.is_set():
        uid: bytearray = tapper_instance.read_passive_target(timeout=0.5)
        if uid is not None:
            logger.info(
                f"Tag detected: {''.join([format(i, '02x').lower() for i in uid])}"
            )
            logger.debug(f"UID: {uid}")

            main.process_tag(tapper_instance, uid)


@logger.catch()
def _tamper_thread(tapper_instance: tapper.Tapper, stop_event: threading.Event) -> None:
    """Thread for checking the tamper switch."""
    while not stop_event.is_set():
        tapper_instance.lock_buzzer.acquire()

        try:
            if tapper_instance.get_tamper():  # TODO: negate for production
                tapper_instance.mqtt_schedule(
                    "event/tamper",
                    {"state": "active" if tapper_instance.get_tamper() else "inactive"},
                )
                logger.warning(f"Tamper detected: {time.time()}")

                tapper_instance.buzzer.on()

            else:
                tapper_instance.buzzer.off()
        finally:
            tapper_instance.lock_buzzer.release()


@logger.catch()
def _heartbeat_thread(
    tapper_instance: tapper.Tapper,
    stop_event: threading.Event,
) -> None:
    """Thread for publishing heartbeat stats."""
    while not stop_event.is_set():
        cpu_temperature = psutil.sensors_temperatures()["cpu_thermal"][0]
        tapper_instance.mqtt_schedule(
            "stats",
            {
                "system": {
                    "uptime": f"{time.time() - psutil.boot_time()}",
                    "cpu": psutil.cpu_percent(),
                    "memory": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage("/").percent,
                    "temperature": cpu_temperature.current,
                },
                "tamper": {
                    "state": "active" if tapper_instance.get_tamper() else "inactive"
                },
            },
        )

        logger.trace(
            json.dumps(
                {
                    "stats": {
                        "system": {
                            "uptime": f"{time.time() - psutil.boot_time()}",
                            "cpu": psutil.cpu_percent(),
                            "memory": psutil.virtual_memory().percent,
                            "disk": psutil.disk_usage("/").percent,
                            "temperature": cpu_temperature.current,
                        },
                        "tamper": {
                            "state": "active"
                            if tapper_instance.get_tamper()
                            else "inactive"
                        },
                    },
                }
            ),
        )

        time.sleep(60)


def start_threads(tapper_instance: tapper.Tapper) -> None:
    """Start TAPPER threads."""
    stop_event: threading.Event = threading.Event()

    tag_thread: threading.Thread = threading.Thread(
        target=_tag_thread,
        args=(
            tapper_instance,
            stop_event,
        ),
    )
    tamper_thread: threading.Thread = threading.Thread(
        target=_tamper_thread,
        args=(
            tapper_instance,
            stop_event,
        ),
    )
    heartbeat_thread: threading.Thread = threading.Thread(
        target=_heartbeat_thread,
        args=(
            tapper_instance,
            stop_event,
        ),
    )
    mqtt_thread: threading.Thread = threading.Thread(
        target=tapper_instance.mqtt_run, args=(stop_event,)
    )

    threads = [tag_thread, tamper_thread, heartbeat_thread, mqtt_thread]

    for t in threads:
        t.start()

    while not stop_event.is_set():
        pending = signal.sigpending()
        if pending:
            logger.warning(f"Pending signals: {pending}")
            stop_event.set()
        time.sleep(1)
