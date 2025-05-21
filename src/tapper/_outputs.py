"""Processing of requests for outputs."""

import json
import threading
import time

from loguru import logger

import tapper


@logger.catch()
def process_request(tapper_instance: tapper.Tapper, request_message: str) -> dict:
    """Process output request.

    Args:
        tapper_instance (): instance of the Tapper class
        request_message (): request message to process, in JSON format
    """
    request: dict = json.loads(request_message)

    request_id: int = request["id"]

    logger.debug(f"Processing request: {request}")

    try:
        if "output" in request.keys():
            match request["output"]["command"]:
                case "activate":
                    tapper_instance.lock_relay.acquire()

                    try:
                        tapper_instance.relay.on()
                    finally:
                        tapper_instance.lock_relay.release()

                case "deactivate":
                    tapper_instance.lock_relay.acquire()

                    try:
                        tapper_instance.relay.off()
                    finally:
                        tapper_instance.lock_relay.release()

                case "pulse":
                    tapper_instance.lock_relay.acquire()

                    try:
                        tapper_instance.relay.on()
                        time.sleep(request["output"]["duration"])
                        tapper_instance.relay.off()
                    finally:
                        tapper_instance.lock_relay.release()

        if "visual" in request:
            if "state" in request["visual"]:
                match request["visual"]["state"][:2]:
                    case "off":
                        tapper_instance.lock_led.acquire()

                        try:
                            tapper_instance.led.off()
                        finally:
                            tapper_instance.lock_led.release()

                    case "on/":
                        tapper_instance.lock_led.acquire()

                        try:
                            match request["visual"]["state"][3:]:
                                case "red":
                                    tapper_instance.led.color = (1, 0, 0)
                                case "green":
                                    tapper_instance.led.color = (0, 1, 0)
                                case "blue":
                                    tapper_instance.led.color = (0, 0, 1)
                                case "yellow":
                                    tapper_instance.led.color = (1, 1, 0)
                        finally:
                            tapper_instance.lock_led.release()

            elif "pattern" in request["visual"]:
                pattern, color = request["visual"].split("/", 1)

                match color:
                    case "red":
                        _do_pattern(
                            pattern,
                            tapper_instance.lock_led,
                            setattr,
                            (tapper_instance.led, "color", (1, 0, 0)),
                            tapper_instance.led.off,
                            (),
                        )

                    case "green":
                        _do_pattern(
                            pattern,
                            tapper_instance.lock_led,
                            setattr,
                            (tapper_instance.led, "color", (0, 1, 0)),
                            tapper_instance.led.off,
                            (),
                        )

                    case "blue":
                        _do_pattern(
                            pattern,
                            tapper_instance.lock_led,
                            setattr,
                            (tapper_instance.led, "color", (0, 0, 1)),
                            tapper_instance.led.off,
                            (),
                        )

                    case "yellow":
                        _do_pattern(
                            pattern,
                            tapper_instance.lock_led,
                            setattr,
                            (tapper_instance.led, "color", (1, 1, 0)),
                            tapper_instance.led.off,
                            (),
                        )

        if "acoustic" in request:
            pattern = request["acoustic"]["pattern"]

            _do_pattern(
                pattern,
                tapper_instance.lock_buzzer,
                tapper_instance.buzzer.on,
                (),
                tapper_instance.buzzer.off,
                (),
            )
    except Exception as e:
        return {"id": request_id, "result": "error", "error": str(e)}

    return {
        "id": request_id,
        "result": "success",
    }


def _do_pattern(
    pattern: str,
    lock: threading.Lock,
    on: callable,
    on_args: tuple,
    off: callable,
    off_args: tuple,
) -> None:
    """Execute a pattern on the output.

    Args:
        pattern (): pattern to execute, possible values are "p1", "p2", "p3", "p4"
        lock (): lock to acquire before executing the pattern
        on (): function to call when switching on the output, for example: tapper_instance.buzzer_pin.on
        on_args (): positional arguments to pass to the on callable
        off (): function to call when switching on the output, for example: tapper_instance.buzzer_pin.off
        off_args (): positional arguments to pass to the off callable
    """
    logger.debug(f"Executing pattern: {pattern}")

    match pattern:
        case "p1":
            lock.acquire()

            try:
                on(*on_args)
                time.sleep(0.5)
                off(*off_args)
            finally:
                lock.release()

        case "p2":
            lock.acquire()

            try:
                for i in range(2):
                    on(*on_args)
                    time.sleep(0.5)
                    off(*off_args)
                    time.sleep(0.25)
            finally:
                lock.release()

        case "p3":
            lock.acquire()

            try:
                for i in range(3):
                    on(*on_args)
                    time.sleep(0.5)
                    off(*off_args)
                    time.sleep(0.25)
            finally:
                lock.release()

        case "p4":
            lock.acquire()

            try:
                for i in range(4):
                    on(*on_args)
                    time.sleep(0.125)
                    off(*off_args)
                    time.sleep(0.125)

            finally:
                lock.release()


@logger.catch()
def add_to_request_queue(client, userdata, message):
    """Add a request to the request queue."""
    logger.debug(f"Received request: {message.payload.decode('utf-8')}")
    logger.debug(f"Request queue: {userdata.get('requests')}")
    request_message: str = message.payload.decode("utf-8")
    userdata.get("requests").put(request_message)
