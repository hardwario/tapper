import json
import queue
import signal
import threading
import time

import psutil
from loguru import logger

import tapper
from tapper import _main as main
from tapper import _outputs as tapper_outputs


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

        stop_event.wait(timeout=2)


@logger.catch()
def _tamper_thread(tapper_instance: tapper.Tapper, stop_event: threading.Event) -> None:
    """Thread for checking the tamper switch."""
    while not stop_event.is_set():
        tapper_instance.lock_buzzer.acquire()

        try:
            if not tapper_instance.get_tamper():  # TODO: negate for production
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
            time.sleep(0.5)


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

        stop_event.wait(timeout=60)


@logger.catch()
def _outputs_thread(tapper_instance: tapper.Tapper, stop_event: threading.Event):
    """Loops processing output requests."""
    while not stop_event.is_set():
        try:
            requests: queue.Queue = tapper_instance.request_queue.get(timeout=0.1)

            payload: dict = tapper_outputs.process_request(tapper_instance, requests)

            tapper_instance.mqtt_schedule("control/response", payload)
        except queue.Empty:
            pass


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
    outputs_thread: threading.Thread = threading.Thread(
        target=_outputs_thread, args=(tapper_instance, stop_event)
    )
    mqtt_thread: threading.Thread = threading.Thread(
        target=tapper_instance.mqtt_run, args=(stop_event,)
    )

    def signal_handler(signum, frame):
        logger.info("Signal received, stopping threads...")
        stop_event.set()
        logger.debug("Stop event set")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    threads = [tag_thread, tamper_thread, heartbeat_thread, outputs_thread, mqtt_thread]

    for t in threads:
        t.start()

    stop_event.wait()

    for t in threads:
        logger.debug(f"Stopping thread {t.name}")
        t.join()

    logger.info("All threads stopped.")
