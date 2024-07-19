import time

import requests

from utils.tiktok_errors import AgeRestricted
from utils.utils import logutil


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
