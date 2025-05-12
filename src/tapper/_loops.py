import asyncio
import json
import signal
from time import sleep, time

import psutil
from loguru import logger

import tapper
from tapper import _main as main


@logger.catch()
async def _cleanup(tapper_instance: tapper.Tapper) -> None:
    """Clean up on termination."""
    logger.info("Cleaning up...")

    tapper_instance.buzzer.off()

    tapper_instance.mqtt_client.disconnect()

    logger.info("Cleanup complete.")

    sleep(2)  # Let logtail finish


@logger.catch()
async def _tag_loop(
    tapper_instance: tapper.Tapper, shutdown_event: asyncio.Event
) -> None:
    """Asyncio loop for reading NFC Tags.

    This is an asyncio loop detecting a tag and sending its UID for processing.

    Args:
        tapper_instance (tapper.Tapper): the Tapper instance
        shutdown_event (asyncio.Event): event to signal the shutdown event
    """
    while not shutdown_event.is_set():
        uid: bytearray = tapper_instance.read_passive_target(timeout=0.5)
        if uid is not None:
            logger.info(f"Tag detected: {' '.join([format(i, '#04x') for i in uid])}")
            logger.debug(f"UID: {uid}")

            await main.process_tag(tapper_instance, uid)

        await asyncio.sleep(0.1)


@logger.catch()
async def _tamper_loop(
    tapper_instance: tapper.Tapper, shutdown_event: asyncio.Event
) -> None:
    """Asyncio loop checking the tamper switch.

    Args:
        tapper_instance (tapper.Tapper): the Tapper instance
        shutdown_event (asyncio.Event): event to signal the shutdown event
    """
    while not shutdown_event.is_set():
        await tapper_instance.lock_buzzer.acquire()

        try:
            if tapper_instance.get_tamper():  # TODO: negate for production
                await tapper_instance.mqtt_publish(
                    "event/tamper",
                    {"state": "active" if tapper_instance.get_tamper() else "inactive"},
                )
                logger.warning(f"Tamper detected: {time()}")

                tapper_instance.buzzer.on()

            else:
                tapper_instance.buzzer.off()
        finally:
            tapper_instance.lock_buzzer.release()

        await asyncio.sleep(0.25)


@logger.catch()
async def _heartbeat_loop(
    tapper_instance: tapper.Tapper, shutdown_event: asyncio.Event
) -> None:
    """Asyncio loop for sending a heartbeat.

    Args:
        tapper_instance (tapper.Tapper): the Tapper instance
        shutdown_event (asyncio.Event): event to signal the shutdown event
    """
    while not shutdown_event.is_set():
        cpu_temperature = psutil.sensors_temperatures()["cpu_thermal"][0]
        await tapper_instance.mqtt_publish(
            "stats",
            {
                "system": {
                    "uptime": f"{time() - psutil.boot_time()}",
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
                            "uptime": f"{time() - psutil.boot_time()}",
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

        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=60
            )  # Make sleep interruptable
        except asyncio.TimeoutError:
            pass


async def loops(tapper_instance: tapper.Tapper) -> None:
    """Gather TAPPER loops.

    Args:
        tapper_instance (tapper.Tapper): the Tapper instance
    """
    shutdown_event: asyncio.Event = asyncio.Event()

    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    await asyncio.gather(
        _tag_loop(tapper_instance, shutdown_event),
        _tamper_loop(tapper_instance, shutdown_event),
        _heartbeat_loop(tapper_instance, shutdown_event),
    )

    await _cleanup(tapper_instance)
