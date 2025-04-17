import asyncio
import json
import signal
from time import sleep, time

import psutil
from loguru import logger

import tapper.main as main
from tapper.tapper import Tapper


@logger.catch()
async def cleanup(tapper: Tapper) -> None:
    """Clean up on termination."""
    logger.info("Cleaning up...")
    tapper.buzzer.off()
    await tapper.mqtt_publish("device", "shutdown")
    tapper.mqtt_client.disconnect()
    logger.info("Cleanup complete.")
    sleep(2)  # Let logtail finish


@logger.catch()
async def tag_loop(tapper: Tapper, shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set():
        uid = tapper.read_passive_target(timeout=0.5)
        if uid is not None:
            logger.info(f"Tag detected: {' '.join([format(i, '#04x') for i in uid])}")
            logger.debug(f"UID: {uid}")
            await main.process_tag(tapper, uid)

        await asyncio.sleep(0.1)


@logger.catch()
async def tamper_loop(tapper: Tapper, shutdown_event: asyncio.Event) -> None:
    await tapper.mqtt_publish("tamper/init", tapper.tamper)

    while not shutdown_event.is_set():
        await tapper.lock_buzzer.acquire()

        try:
            if tapper.tamper:  # TODO: negate for production
                await tapper.mqtt_publish("tamper/event", "Tamper detected!")
                logger.warning(f"Tamper detected: {time()}")

                tapper.buzzer.on()

            else:
                tapper.buzzer.off()
        finally:
            tapper.lock_buzzer.release()

        await asyncio.sleep(0.25)


@logger.catch()
async def heartbeat_loop(tapper: Tapper, shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set():
        await tapper.mqtt_publish(
            "heartbeat",
            {
                "id": tapper.id,
                "uptime": f"{time() - psutil.boot_time()}",
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
            },
        )
        logger.debug(
            json.dumps(
                {
                    "heartbeat": {
                        "id": tapper.id,
                        "uptime": f"{time() - psutil.boot_time()}",
                        "cpu": psutil.cpu_percent(),
                        "memory": psutil.virtual_memory().percent,
                        "disk": psutil.disk_usage("/").percent,
                    }
                }
            ),
        )

        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=60
            )  # Make sleep interruptable
        except asyncio.TimeoutError:
            pass


async def loops(tapper: Tapper) -> None:
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    await asyncio.gather(
        tag_loop(tapper, shutdown_event),
        tamper_loop(tapper, shutdown_event),
        heartbeat_loop(tapper, shutdown_event),
    )

    await cleanup(tapper)
