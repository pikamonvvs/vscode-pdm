import os
import sys
from datetime import datetime

from loguru import logger


class LogUtil:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LogUtil, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir="logs", log_level="INFO", rotation="10 MB", retention="10 days", compression="zip"):
        if self._initialized:
            return
        self.log_dir = log_dir
        self.log_level = log_level
        self.rotation = rotation
        self.retention = retention
        self.compression = compression
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self._setup_logger()
        self._initialized = True

    def _setup_logger(self):
        logger.remove()

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        log_file = os.path.join(self.log_dir, f"{self.current_date}.log")

        logger.add(sys.stdout, level="INFO")
        logger.add(
            log_file,
            level=self.log_level,
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
        )

    def _update_log_file(self):
        new_date = datetime.now().strftime("%Y-%m-%d")
        if new_date != self.current_date:
            self.current_date = new_date
            self._setup_logger()

    def log_debug(self, message):
        self._update_log_file()
        logger.debug(message)

    def log_info(self, message):
        self._update_log_file()
        logger.info(message)

    def log_warning(self, message):
        self._update_log_file()
        logger.warning(message)

    def log_error(self, message):
        self._update_log_file()
        logger.error(message)

    def log_exception(self, message):
        self._update_log_file()
        logger.exception(message)


def main():
    logutil = LogUtil()
    logutil.log_debug("This is a debug message.")
    logutil.log_info("This is an info message.")
    logutil.log_warning("This is a warning message.")
    logutil.log_error("This is an error message.")
    try:
        1 / 0
    except ZeroDivisionError:
        logutil.log_exception("An exception occurred.")


if __name__ == "__main__":
    main()
