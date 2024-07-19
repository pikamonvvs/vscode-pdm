import asyncio

import utils.config as config
import utils.utils as utils
from recorders.recorders_chzzk import *
from recorders.recorders_chzzk import recording
from utils.utils import logutil


async def run():
    args = utils.parse_args()
    try:
        platform = globals()[args.get(config.KEY_PLATFORM)]
        coroutine = platform(args).start()
        await coroutine
    except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        logutil.warning("The user has interrupted the recording. Closing the live stream.")
        for stream_fd, output in recording.copy().values():
            stream_fd.close()
            output.close()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
