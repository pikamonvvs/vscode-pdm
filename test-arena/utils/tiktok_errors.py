from enum import Enum


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
