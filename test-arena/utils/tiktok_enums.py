from enum import IntEnum


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
