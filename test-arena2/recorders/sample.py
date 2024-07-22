import sys

import requests

from recorders.recorder import LiveRecorder
from utils.utils import logutil


class TK(LiveRecorder):
    def __init__(self, user: dict):
        super().__init__(user)
        self.flag = f"[{self.platform}][{self.id}]"

        self.room_id = None
        self.req = requests
        if self.proxy:
            self.req = get_proxy_session(self.proxy)

        self.status = LiveStatus.BOT_INIT
        self.out_file = None
        self.video_list = [str]

    def run(self):
        try:
            if self.status == LiveStatus.LAGGING:
                retry_wait(WaitTime.LAG, False)
            if not self.room_id:
                self.room_id = self.test_get_room_id_from_user()
            if not self.room_id:
                self.room_id = self.get_room_id_from_user()
            if not self.name:
                self.name = self.get_user_from_room_id()
            if self.status == LiveStatus.BOT_INIT:
                logutil.info(self.flag, f"Username: {self.name}")
                logutil.info(self.flag, f"Room ID: {self.room_id}")

            self.status = self.is_user_live()

            if self.status == LiveStatus.OFFLINE:
                logutil.info(self.flag, f"{self.name} is offline")
                self.room_id = None
                if self.out_file:
                    self.finish_recording()
                else:
                    retry_wait(self.interval, False)
            elif self.status == LiveStatus.LAGGING:
                live_url = self.get_live_url()
                self.start_recording(live_url)
            elif self.status == LiveStatus.LIVE:
                logutil.info(self.flag, f"{self.name} is live")
                live_url = self.get_live_url(self.room_id)
                logutil.info(self.flag, f"Live URL: {live_url}")
                self.start_recording(live_url)

        except (GenericReq, ValueError, requests.HTTPError, BrowserExtractor, ConnectionClosed, UserNotFound) as e:
            if "room_id not found" in str(e):
                logutil.info(self.flag, e)
            else:
                logutil.error(self.flag, e)
            self.room_id = None
            retry_wait(self.interval)
        except Blacklisted as e:
            logutil.error(self.flag, ErrorMsg.BLKLSTD_AUTO_MODE_ERROR)
            raise e
        except KeyboardInterrupt:
            logutil.warning(self.flag, "Stopped by keyboard interrupt.")
            sys.exit(0)
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            retry_wait(self.interval)


######################################################################################################################################################


def lag_error(err_str) -> bool:
    """Check if ffmpeg output indicates that the stream is lagging"""
    lag_errors = ["Server returned 404 Not Found", "Stream ends prematurely", "Error in the pull function"]
    return any(err in err_str for err in lag_errors)


def retry_wait(seconds=60, print_msg=True):
    """Sleep for the specified number of seconds"""
    if print_msg:
        if seconds < 60:
            logutil.info(f"Waiting {seconds} seconds")
        else:
            logutil.info(f"Waiting {'%g' % (seconds / 60)} minute{'s' if seconds > 60 else ''}")
    time.sleep(seconds)


def check_exists(exp, value):
    """Check if a nested json key exists"""
    # For the case that we have an empty element
    if exp is None:
        return False
    # Check existence of the first key
    if value[0] in exp:
        # if this is the last key in the list, then no need to look further
        if len(value) == 1:
            return True
        else:
            next_value = value[1 : len(value)]
            return check_exists(exp[value[0]], next_value)
    else:
        return False


def get_proxy_session(proxy_url):
    """Request with TOR or other proxy.
    TOR uses 9050 as the default socks port.
    To (hopefully) prevent getting home IP blacklisted for bot activity.
    """
    try:
        logutil.info(f"Using proxy: {proxy_url}")
        session = requests.session()
        session.proxies = {"http": proxy_url, "https": proxy_url}
        # logutil.info("regular ip:")
        # logutil.info(req.get("http://httpbin.org/ip").text)
        # logutil.info("proxy ip:")
        # logutil.info(session.get("http://httpbin.org/ip").text)
        return session
    except Exception as ex:
        logutil.error(ex)
        return requests


def login_required(json) -> bool:
    # logutil.info(json)
    if check_exists(json, ["data", "prompts"]) and "This account is private" in json["data"]["prompts"]:
        logutil.info("Account is private")
        return True
    elif check_exists(json, ["status_code"]) and json["status_code"] == 4003110:
        raise AgeRestricted("Account is age restricted")
    else:
        return False


class LiveStatus(IntEnum):
    """Enumeration that defines potential states of the live stream"""

    BOT_INIT = 0
    LAGGING = 1
    LIVE = 2
    OFFLINE = 3


class WaitTime(IntEnum):
    """Enumeration that defines wait times in seconds."""

    LONG = 120
    SHORT = 10
    LAG = 5


class StatusCode(IntEnum):
    """Enumeration that defines HTTP status codes."""

    OK = 200
    REDIRECT = 302
    BAD_REQUEST = 400


class Mode(IntEnum):
    """Enumeration that represents the recording modes."""

    MANUAL = 0
    AUTOMATIC = 1


class ErrorMsg(Enum):
    """Enumeration of error messages"""

    def __str__(self):
        return str(self.value)

    BLKLSTD_AUTO_MODE_ERROR: str = (
        "Automatic mode can be used only in unblacklisted country. Use a VPN\n[*] "
        "Unrestricted country list: "
        "https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE.md#unrestricted"
        "-country"
    )
    BLKLSTD_ERROR = (
        "Captcha required or country blocked. Use a vpn or room_id."
        "\nTo get room id: https://github.com/Michele0303/TikTok-Live-Recorder/blob/main/GUIDE.md#how-to-get-room_id"
        "\nUnrestricted country list: https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE"
        ".md#unrestricted-country"
    )
    USERNAME_ERROR = "Error: Username/Room_id not found or the user has never been in live"
    CONNECTION_CLOSED = "Connection broken by the server."


class Info(Enum):
    """Enumeration that defines the version number and the banner message."""

    def __str__(self):
        return str(self.value)

    VERSION = 4.2
    BANNER = f"Tiktok Live Recorder v{VERSION}"


class ConnectionClosed(Exception):
    pass


class UserNotFound(Exception):
    pass


class LoginRequired(Exception):
    pass


class AgeRestricted(Exception):
    pass


class Blacklisted(Exception):
    pass


class Recording(Exception):
    pass


class BrowserExtractor(Exception):
    pass


class GenericReq(Exception):
    pass


class FFmpeg(Exception):
    pass


class StreamLagging(Exception):
    pass
