import argparse
import signal
import sys
import time

from loguru import logger

PLATFORM_CHOICES = [
    "Afreeca",
    "Chzzk",
    "TikTok",
]
FORMAT_CHOICES = ["mp4", "ts", "flv"]


def parse_args():
    parser = argparse.ArgumentParser(description="Print a welcome message and accept various settings.")
    parser.add_argument("platform", type=str, choices=PLATFORM_CHOICES, help="Name of the platform")
    parser.add_argument("id", type=str, help="ID of the user")
    parser.add_argument("-n", "--name", type=str, help="Specify a name")
    parser.add_argument("-i", "--interval", type=int, help="Set interval time in seconds")
    parser.add_argument("-f", "--format", type=str, choices=FORMAT_CHOICES, help="Set the output format")
    parser.add_argument("-o", "--output", type=str, help="Specify the output file path")
    parser.add_argument("-p", "--proxy", type=str, help="Set the proxy server")
    parser.add_argument("-c", "--cookies", type=str, help="Set the cookies file path")
    parser.add_argument("-H", "--headers", type=str, help="Set the headers")
    parser.add_argument("-l", "--log-level", type=str, help="Set the logging level")

    args = parser.parse_args()

    # Create a dictionary from the arguments and filter out None values
    args_dict = {key: value for key, value in vars(args).items() if value is not None}

    return args_dict


class Logger:
    def __init__(self):
        self.configure_logger()

    def configure_logger(self):
        logger.add(
            sink="logs/log_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="3 days",
            level="INFO",
            encoding="utf-8",
            format="[{time:YYYY-MM-DD HH:mm:ss}][{level}][{name}][{function}:{line}]{message}",
        )
        # logger.add("logs/log_general.txt", rotation="10MB", retention="10 days")
        # logger.add("logs/log_info.txt", rotation="10MB", retention="10 days", level="INFO")
        # logger.add("logs/log_warning.txt", rotation="10MB", retention="10 days", level="WARNING")
        logger.add(
            sink="logs/log_{time:YYYY-MM-DD}_error.log",
            rotation="00:00",
            retention="3 days",
            encoding="utf-8",
            format="[{time:YYYY-MM-DD HH:mm:ss}][{level}][{name}][{function}:{line}]{message}",
        )

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

    def exception(self, *args):
        message = " ".join(str(arg) for arg in args)
        logger.exception(message)


logutil = Logger()


def signal_handler(sig, frame):
    print("SIGTERM detected. Exiting gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    logutil.info("version = 1.0.0")
    signal.signal(signal.SIGTERM, signal_handler)
    args = parse_args()
    seconds = 10
    try:
        for sec in range(seconds):
            logger.info(f"Counting: {sec + 1}/{seconds}, args: {args}")
            time.sleep(1)
        logutil.info("Finished counting")
    except KeyboardInterrupt:
        logutil.warning("KeyboardInterrupt detected")
    except Exception as e:
        logutil.error(f"An error occurred: {e}")
