# SPDX-License-Identifier: MIT
import sys

from loguru import logger


@logger.catch
def logger_start(debug: bool) -> None:
    """Set up Logger for TAPPER run."""
    if debug:
        logger.add(sys.stderr, level="DEBUG", enqueue=True, colorize=True)
    else:
        logger.add(sys.stdout, level="INFO", enqueue=True, colorize=True)
