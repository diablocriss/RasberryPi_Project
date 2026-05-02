import logging
from logging.config import fileConfig
from pathlib import Path


def setup_logging(config_path: str | Path = "configs/logger.conf") -> None:
    path = Path(config_path)
    if path.exists():
        fileConfig(path, disable_existing_loggers=False)
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
