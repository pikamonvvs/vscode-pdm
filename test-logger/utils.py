from loguru import logger


class Logger:
    def __init__(self):
        self.configure_logger()

    def configure_logger(self):
        logger.add("log_general.txt", rotation="10MB", retention="10 days")
        logger.add("log_info.txt", rotation="10MB", retention="10 days", level="INFO")
        logger.add("log_warning.txt", rotation="10MB", retention="10 days", level="WARNING")
        logger.add("log_error.txt", rotation="10MB", retention="10 days", level="ERROR")

    def debug(self, *args):
        message = " ".join(str(arg) for arg in args)
        logger.debug(message)

    def info(self, *args):
        message = " ".join(str(arg) for arg in args)
        logger.info(message)

    def warning(self, *args):
        message = " ".join(str(arg) for arg in args)
        logger.warning(message)

    def error(self, *args):
        message = " ".join(str(arg) for arg in args)
        logger.error(message)


logutil = Logger()
