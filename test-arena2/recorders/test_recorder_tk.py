import io
import os
import sys
import time

import ffmpeg
import requests

from recorders.recorder import LiveRecorder
from utils.utils import logutil


class TikTok(LiveRecorder):
    def __init__(self, user: dict):
        super().__init__(user)
        self.flag = f"[{self.platform}][{self.id}]"
        self.room_id = None
        self.req = requests
        if self.proxy:
            self.req = self.get_proxy_session(self.proxy)
        self.out_file = None
        self.video_list = [str]

    def run(self):
        try:
            if not self.room_id:
                self.room_id = self.test_get_room_id_from_user()
            if not self.room_id:
                self.room_id = self.get_room_id_from_user()
            if not self.name:
                self.name = self.get_user_from_room_id()

            logutil.info(self.flag, f"Username: {self.name}")
            logutil.info(self.flag, f"Room ID: {self.room_id}")

            if not self.is_user_live():
                logutil.info(self.flag, f"{self.name} is offline")
                self.room_id = None
                if self.out_file:
                    self.finish_recording()
                else:
                    time.sleep(self.interval)
            else:
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
                logutil.error(self.flag, f"Unexpected Error: {e}")
            self.room_id = None
            time.sleep(self.interval)

    def start_recording(self, live_url):
        """Start recording live"""
        should_exit = False
        title = self.test_get_title(self.room_id)
        output_file = self.get_filename(title, self.format)
        self.out_file = os.path.join(self.output, output_file)
        logutil.info(self.flag, f"Output directory: {self.output}")
        try:
            self.handle_recording_ffmpeg(live_url)
        except Exception as e:
            if isinstance(e, KeyboardInterrupt):
                logutil.info(self.flag, "Recording stopped by keyboard interrupt")
                should_exit = True
            elif "Stream lagging" in str(e):
                logutil.info(self.flag, "Stream lagging")
            elif "FFmpeg" in str(e):
                logutil.error(self.flag, f"FFmpeg Error: {e}")
            elif "FFmpeg is not installed" in str(e):
                logutil.error(self.flag, "FFmpeg is not installed.")
                raise e
            else:
                logutil.error(self.flag, f"Recording Error: {e}")

        try:
            if os.path.getsize(self.out_file) < 1048576:
                os.remove(self.out_file)
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
                        logutil.info(self.flag, last_stats)
                        stats_shown = True
                    else:
                        ffmpeg_err += line
            if ffmpeg_err:
                if self.lag_error(ffmpeg_err):
                    raise Exception("Stream lagging")
                else:
                    raise Exception(ffmpeg_err.strip())
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
                    raise Exception(ffmpeg_err.strip())
                logutil.info(self.flag, "Concat finished")
                for v in self.video_list:
                    os.remove(v)
                logutil.info(self.flag, f"Deleted {len(self.video_list)} video files")
            if os.path.isfile(self.out_file):
                logutil.info(self.flag, f"Recording finished: {self.out_file}")
            if os.path.exists(ffmpeg_concat_list):
                os.remove(ffmpeg_concat_list)
                logutil.info(self.flag, "Removed ffmpeg_concat_list.")
        except Exception as e:
            logutil.error(self.flag, f"Unexpected Error: {e}")
        finally:
            self.video_list = []
            self.out_file = None

    def is_user_live(self):
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
        try:
            response = self.req.get(url, headers=self.headers)
            if response.status_code != 200:
                logutil.error(self.flag, f"Failed to load the page. Status code: {response.status_code}")
                return False
            if not response.content:
                logutil.error(self.flag, "Response content is empty.")
                return False
            response_json = response.json()
            status = response_json.get("LiveRoomInfo", {}).get("status")
            if not status:
                logutil.error(f"LiveRoomInfo.status not found in json: {response_json}")
                return False
            return status != 4
        except Exception as e:
            logutil.error(self.flag, f"Unexpected Error: {e}")
            raise e

    def get_live_url(self, room_id):
        """Get the CDN (flv or m3u8) of the stream."""
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
            if self.check_login_required(response_json):
                logutil.error(self.flag, "Login required")
                return ""
            rtmp_pull_url = response_json.get("data", {}).get("stream_url", {}).get("rtmp_pull_url")
            if not rtmp_pull_url:
                logutil.error(self.flag, f"Stream URL not found in json: {response_json}")
                return ""
            return rtmp_pull_url
        except Exception as e:
            logutil.error(self.flag, f"Unexpected Error: {e}")
            raise e

    def lag_error(self, err_str) -> bool:
        """Check if ffmpeg output indicates that the stream is lagging"""
        lag_errors = ["Server returned 404 Not Found", "Stream ends prematurely", "Error in the pull function"]
        return any(err in err_str for err in lag_errors)

    def check_exists(self, exp, value):
        """Check if a nested json key exists"""
        if exp is None:
            return False
        if value[0] in exp:
            if len(value) == 1:
                return True
            else:
                next_value = value[1:]
                return self.check_exists(exp[value[0]], next_value)
        else:
            return False

    def get_proxy_session(self, proxy_url):
        """Request with TOR or other proxy. TOR uses 9050 as the default socks port. To (hopefully) prevent getting home IP blacklisted for bot activity."""
        try:
            logutil.info(f"Using proxy: {proxy_url}")
            session = requests.Session()
            session.proxies = {"http": proxy_url, "https": proxy_url}
            return session
        except Exception as ex:
            logutil.error(ex)
            return requests

    def check_login_required(self, json) -> bool:
        prompts = json.get("data", {}).get("prompts")
        if "This account is private" in prompts:
            logutil.info("Account is private")
            return True
        status_code = json.get("status_code")
        if status_code == 4003110:
            logutil.error("Account is age restricted")
            return True
        return False
