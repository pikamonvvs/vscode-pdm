from loguru import logger
from recorders import *

import utils


def main():
    logger.add(
        sink="logs/log_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="3 days",
        level="INFO",
        encoding="utf-8",
        format="[{time:YYYY-MM-DD HH:mm:ss}][{level}][{name}][{function}:{line}]{message}",
    )
    args = utils.parse_args()
    platform = globals()[args.get("platform")]
    platform(args).run()


if __name__ == "__main__":
    main()
