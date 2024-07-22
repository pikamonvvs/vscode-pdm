import io
import json
import os
import re
import sys
import time
from enum import Enum, IntEnum

import ffmpeg
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, SSLError

from recorders.recorder import LiveRecorder
from utils.utils import logutil


class TikTok(LiveRecorder):
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
                retry_wait(5, False)
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

        except KeyboardInterrupt:
            logutil.warning(self.flag, "Stopped by keyboard interrupt.")
            sys.exit(0)
        except Exception as e:
            if "not found" in str(e):
                logutil.info(self.flag, e)
            else:
                logutil.error(self.flag, f"Unexpected error: {e}")
            self.room_id = None
            retry_wait(self.interval)

    def start_recording(self, live_url):
        """Start recording live"""
        should_exit = False

        title = self.test_get_title(self.room_id)
        output_file = self.get_filename(title, self.format)
        self.out_file = os.path.join(self.output, output_file)

        if self.status is not LiveStatus.LAGGING:
            logutil.info(self.flag, f"Output directory: {self.output}")

        try:
            self.handle_recording_ffmpeg(live_url)
        except StreamLagging:
            logutil.info(self.flag, "Stream lagging")
        except FFmpeg as e:
            logutil.error(self.flag, f"FFmpeg error: {e}")
        except FileNotFoundError as e:
            logutil.error(self.flag, "FFmpeg is not installed.")
            raise e
        except KeyboardInterrupt:
            logutil.info(self.flag, "Recording stopped by keyboard interrupt")
            should_exit = True
        except Exception as e:
            logutil.error(self.flag, f"Recording error: {e}")

        self.status = LiveStatus.LAGGING

        try:
            if os.path.getsize(self.out_file) < 1048576:
                os.remove(self.out_file)
                # logutil.info(self.flag, "removed file < 1MB")
            else:
                self.video_list.append(self.out_file)
        except FileNotFoundError:
            pass
        except Exception as e:
            logutil.error(self.flag, e)

        if should_exit:
            self.finish_recording()
            sys.exit(0)

    def handle_recording_ffmpeg(self, live_url):
        """Show real-time stats and raise ffmpeg errors"""
        stats_shown = False

        try:
            process = (
                ffmpeg.input(live_url, loglevel="error", reconnect=1, reconnect_streamed=1, reconnect_at_eof=1, reconnect_delay_max=5, timeout=10000000, stats=None)
                .output(self.out_file, c="copy")
                .run_async(pipe_stderr=True)
            )
            ffmpeg_err = ""
            last_stats = ""
            text_stream = io.TextIOWrapper(process.stderr, encoding="utf-8")

            while process.poll() is None:
                for line in text_stream:
                    line = line.strip()
                    if "frame=" in line:
                        last_stats = line
                        if not stats_shown:
                            logutil.info(self.flag, "Started recording")
                            logutil.info(self.flag, "Press 'q' to re-start recording, CTRL + C to stop")
                            self.status = LiveStatus.LIVE
                        logutil.info(self.flag, last_stats)
                        stats_shown = True
                    else:
                        ffmpeg_err += line

            if ffmpeg_err:
                if lag_error(ffmpeg_err):
                    raise StreamLagging
                else:
                    raise FFmpeg(ffmpeg_err.strip())

        except KeyboardInterrupt as i:
            raise i
        except ValueError as e:
            logutil.error(self.flag, e)
        finally:
            if stats_shown:
                logutil.info(self.flag, last_stats)

    def finish_recording(self):
        """Combine multiple videos into one if needed"""
        try:
            current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())
            ffmpeg_concat_list = f"{self.name}_{current_date}_concat_list.txt"

            if len(self.video_list) > 1:
                title = f"{self.test_get_title(self.room_id)}_concat"
                output_file = self.get_filename(title, self.format)
                self.out_file = os.path.join(self.output, output_file)
                logutil.info(self.flag, f"Concatenating {len(self.video_list)} video files")

                with open(ffmpeg_concat_list, "w") as file:
                    for v in self.video_list:
                        file.write(f"file '{v}'\n")

                proc = ffmpeg.input(ffmpeg_concat_list, f="concat", safe=0, loglevel="error").output(self.out_file, c="copy").run_async(pipe_stderr=True)

                text_stream = io.TextIOWrapper(proc.stderr, encoding="utf-8")
                ffmpeg_err = ""

                while proc.poll() is None:
                    for line in text_stream:
                        ffmpeg_err += line

                if ffmpeg_err:
                    raise FFmpeg(ffmpeg_err.strip())

                logutil.info(self.flag, "Concat finished")
                for v in self.video_list:
                    os.remove(v)
                logutil.info(self.flag, f"Deleted {len(self.video_list)} video files")

            if os.path.isfile(self.out_file):
                logutil.info(self.flag, f"Recording finished: {self.out_file}")

            if os.path.exists(ffmpeg_concat_list):
                os.remove(ffmpeg_concat_list)

        except FFmpeg as e:
            logutil.error(self.flag, f"FFmpeg concat error: {e}")
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
        finally:
            self.video_list = []
            self.out_file = None

    def is_user_live(self):
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        try:
            response = self.req.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(self.flag, f"Failed to load the page. Status code: {response.status_code}")
                return LiveStatus.OFFLINE
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return LiveStatus.OFFLINE

            response_json = response.json()
            status = response_json.get("LiveRoomInfo", {}).get("status")
            if not status:
                logutil.error(f"LiveRoomInfo.status not found in json: {response_json}")
                return LiveStatus.OFFLINE

            if status == 4:
                return LiveStatus.OFFLINE

            if self.status != LiveStatus.LAGGING:
                return LiveStatus.LIVE
            else:
                return LiveStatus.LAGGING

        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e

    def get_live_url(self, room_id):
        """Get the CDN (flv or m3u8) of the stream."""
        if self.status is not LiveStatus.LAGGING:
            logutil.info(self.flag, f"Getting live url for room ID {room_id}")

        url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={room_id}"
        try:
            response = self.req.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(self.flag, f"Failed to load the page. Status code: {response.status_code}")
                return ""
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return ""

            response_json = response.json()
            if check_login_required(response_json):
                logutil.error(self.flag, "Login required")
                return ""
            rtmp_pull_url = response_json.get("data", {}).get("stream_url", {}).get("rtmp_pull_url")
            if not rtmp_pull_url:
                logutil.error(self.flag, f"Stream URL not found in json: {response_json}")
                return ""

            return rtmp_pull_url

        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e

    def get_room_id_from_user(self) -> str:
        url = f"https://www.tiktok.com/@{self.id}/live"
        try:
            response = self.req.get(url, headers=self.headers, allow_redirects=False)
            if response.status_code != 200:
                logutil.error(self.flag, f"Failed to load the page. Status code: {response.status_code}")
                if response.status_code == 302:
                    logutil.error(self.flag, "Appears to be blacklisted.")
                    logutil.error(self.flag, ErrorMsg.BLACKLISTED_AUTO_MODE_ERROR)
                return ""
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return ""

            match = re.search(r"room_id=(\d+)", response.text)
            if not match:
                # logutil.error(self.flag, "Room ID not found")
                logutil.info(self.flag, "Room ID not found")
                return ""
            room_id = match.group(1)

            return room_id

        except requests.HTTPError as e:
            logutil.error(self.flag, f"HTTP error: {e}")
            raise e
        except AttributeError as e:
            logutil.error(self.flag, f"Attribute error: {e}")
            raise e
        except ValueError as e:
            logutil.error(self.flag, f"Value error: {e}")
            raise e
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e

    def get_user_from_room_id(self) -> str:
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(self.flag, f"Failed to load the page. Status code: {response.status_code}")
                return ""
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return ""

            response_json = response.json()
            unique_id = response_json.get("LiveRoomInfo", {}).get("ownerInfo", {}).get("uniqueId")
            if not unique_id:
                logutil.error(self.flag, f"Unique ID not found in json: {response_json}")
                return ""

            return unique_id

        except ConnectionAbortedError as e:
            logutil.error(self.flag, f"Connection aborted: {e}")
            raise e
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e

    ##################################################################################################################################################

    def test_get_room_id_from_user(self):
        url = f"https://www.tiktok.com/@{self.id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(f"Failed to load the page. Status code: {response.status_code}")
                return None
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            if not soup:
                logutil.error(self.flag, "Failed to parse the page.")
                return None

            script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
            if not script_tag:
                logutil.error(self.flag, "Cannot find script tag for this ID.")
                return None

            json_data = json.loads(script_tag.string)
            if not json_data:
                logutil.error(self.flag, "Failed to load JSON data.")
                return None

            room_id = json_data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {}).get("roomId")
            if not room_id:
                logutil.info(self.flag, "Cannot find Room ID.")
                return None

            return room_id

        except SSLError as e:
            logutil.error(self.flag, f"SSL error: {e}")
            return None
        except ConnectionError as e:
            logutil.error(self.flag, f"Connection error: {e}")
            return None
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            return None

    def test_get_status(self, room_id):
        url = f"https://webcast.tiktok.com/webcast/room/check_alive/?aid=1988&room_ids={room_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(self.flag, f"Failed to load the page. Status code: {response.status_code}")
                return None
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return None

            response_json = response.json()
            status_code = response_json.get("status_code")
            if status_code != 0:
                logutil.error(self.flag, "Invalid status code")
                return None

            data = response_json.get("data")[0]
            # logutil.debug(self.flag, f"Data: {json.dumps(data, indent=2)}")
            if not data:
                logutil.error(self.flag, "Cannot find data.")
                return None

            alive = data.get("alive")
            # logutil.debug(self.flag, f"Alive: {alive}")
            if alive is None:
                logutil.error(self.flag, "Cannot find alive status.")
                return None

            return alive

        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e

    def test_get_title(self, room_id):
        url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={room_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(f"Failed to load the page. Status code: {response.status_code}")
                return ""
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return ""

            response_json = response.json()
            title = response_json.get("data", {}).get("title")
            if not title:
                logutil.error(self.flag, "Cannot find title.")
                return ""

            return title

        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e


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


def check_login_required(json) -> bool:
    prompts = json.get("data", {}).get("prompts")
    if "This account is private" in prompts:
        logutil.info("Account is private")
        return True

    status_code = json.get("status_code")
    if status_code == 4003110:
        logutil.error("Account is age restricted")
        return True

    return False


class LiveStatus(IntEnum):
    """Enumeration that defines potential states of the live stream"""

    BOT_INIT = 0
    LAGGING = 1
    LIVE = 2
    OFFLINE = 3


class ErrorMsg(Enum):
    """Enumeration of error messages"""

    def __str__(self):
        return str(self.value)

    BLACKLISTED_AUTO_MODE_ERROR: str = (
        "Automatic mode can be used only in unblacklisted country. Use a VPN\n[*] "
        "Unrestricted country list: "
        "https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE.md#unrestricted"
        "-country"
    )
    BLACKLISTED_ERROR = (
        "Captcha required or country blocked. Use a vpn or room_id."
        "\nTo get room id: https://github.com/Michele0303/TikTok-Live-Recorder/blob/main/GUIDE.md#how-to-get-room_id"
        "\nUnrestricted country list: https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE"
        ".md#unrestricted-country"
    )
    USERNAME_ERROR = "Error: Username/Room_id not found or the user has never been in live"
    CONNECTION_CLOSED = "Connection broken by the server."


class FFmpeg(Exception):
    pass


class StreamLagging(Exception):
    pass
