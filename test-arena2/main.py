import asyncio

import utils.utils as utils
from recorders.recorder import *
from recorders.recorder import recording
from utils.utils import logutil


async def run():
    args = utils.parse_args()
    try:
        platform = globals()[args.get("platform")]
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
