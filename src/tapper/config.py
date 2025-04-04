from loguru import logger
from yaml import Loader, load


@logger.catch()
def load_config(filepath) -> dict:
    with open(filepath, "r") as file:
        return load(file, Loader=Loader)
