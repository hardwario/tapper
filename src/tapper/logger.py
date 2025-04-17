import sys

from loguru import logger


@logger.catch
def start(debug: bool, logtail_token: str = None, logtail_host: str = None) -> None:
    """Logger setup for TAPPER run"""

    if debug:
        logger.add(sys.stderr, level="DEBUG", enqueue=True, colorize=True)
    else:
        logger.add(sys.stdout, level="INFO", enqueue=True, colorize=True)

    if logtail_token is not None:
        try:
            from logtail import LogtailHandler

            logtail_handler = LogtailHandler(
                source_token=logtail_token, host=logtail_host
            )
            logger.add(logtail_handler, format="{message}", level="DEBUG", enqueue=True)

        except ModuleNotFoundError:
            logger.warning(
                "Logtail not found. To use this feature install tapper[logtail]."
            )
            pass
