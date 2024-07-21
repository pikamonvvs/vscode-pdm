import os
import re
import sys
import time
from http.cookies import SimpleCookie

import ffmpeg
import httpx
import requests
import streamlink
from httpx_socks import AsyncProxyTransport

from recorders.recorder import LiveRecorder
from utils.utils import logutil


class Chzzk(LiveRecorder):
    def __init__(self, user: dict):
        super().__init__(user)
        self.get_ids()
        self.flag = f"[{self.platform}][{self.name}]"

    def get_id_from_name(self, name):
        try:
            logutil.debug(f"Searching for channel: {name}")
            response = requests.get(f"https://api.chzzk.naver.com/service/v1/search/channels?keyword={name}&size=10", headers=self.headers)
            if response.status_code == 404:
                logutil.error(f"Page not found: {response.url}")
                return None

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            data = response_json["content"]["data"]
            if not data:
                logutil.error(f"Cannot find channel {name}.")
                return None

            for channel in data:
                channel_name = channel["channel"]["channelName"]
                if channel_name == name:
                    channel_id = channel["channel"]["channelId"]
                    if not channel_id:
                        logutil.error("Cannot find channel ID.")
                        return None
                    return channel_id

        except Exception as e:
            logutil.error(f"Error occurred while fetching channel information: {e}")
            return None

        logutil.error(f"Cannot find channel {name}.")
        return None

    def get_ids(self):
        if not self.check_if_id(self.id):
            channel_name = self.id
            channel_id = self.get_id_from_name(channel_name)
            if channel_id is None:
                logutil.error(f"Cannot find channel ID for name {self.id}.")
                return
            self.id = channel_id
            if self.name == self.id:
                self.name = channel_name
        else:
            channel_name = self.get_channel_name(self.id)
            if channel_name is None:
                logutil.error(f"Cannot find channel name for ID {self.id}.")
                return
            self.name = channel_name

    def check_if_id(self, channel):
        # check if the string is a valid channel id
        pattern = re.compile(r"^[0-9a-f]{32}$")
        return bool(pattern.match(channel))

    def is_file(self, file_path):
        return os.path.isfile(file_path)

    def get_cookies(self):
        logutil.info(self.flag, "self.cookies: ", self.cookies)
        if self.cookies:
            cookies = SimpleCookie()
            if self.is_file(self.cookies):
                self.cookies = open(self.cookies, "r").read().strip()
                logutil.info(self.flag, "self.cookies: ", self.cookies)
            cookies.load(self.cookies)
            self.cookies = {k: v.value for k, v in cookies.items()}

    # def get_cookies_from_file(self):
    #     current_script_dir = os.getcwd()
    #     plugins_dir = os.path.join(current_script_dir, "plugins")

    #     if not os.path.exists(plugins_dir):
    #         os.makedirs(plugins_dir)

    #     cookies_file_path = os.path.join(plugins_dir, "cookies.txt")

    #     if not os.path.isfile(cookies_file_path) or os.path.getsize(cookies_file_path) == 0:
    #         logutil.warning("The cookies.txt file does not exist or is empty. Please enter the cookie values.")
    #         logutil.warning("\nReference: https://github.com/BlackOut-git/Chzzk-live-recorder")
    #         NID_AUT = input("Enter the NID_AUT cookie value: ")
    #         NID_SES = input("Enter the NID_SES cookie value: ")
    #         with open(cookies_file_path, "w") as f:
    #             f.write(f"NID_AUT={NID_AUT}; NID_SES={NID_SES};")
    #     else:
    #         logutil.info(f"cookies.txt exists on {cookies_file_path}")

    #     with open(cookies_file_path, "r") as f:
    #         return f.read().strip()

    def get_client(self):
        client_kwargs = {
            "http2": True,
            "timeout": self.interval,
            "limits": httpx.Limits(max_keepalive_connections=100, keepalive_expiry=self.interval * 2),
            "headers": self.headers,
            "cookies": self.cookies,
        }
        # Check if a proxy is set
        if self.proxy:
            if "socks" in self.proxy:
                client_kwargs["transport"] = AsyncProxyTransport.from_url(self.proxy)
            else:
                client_kwargs["proxies"] = self.proxy
        return httpx.AsyncClient(**client_kwargs)

    def get_streamlink(self):
        session = streamlink.Streamlink({"stream-segment-timeout": 60, "hls-segment-queue-threshold": 10})
        # Add streamlink's HTTP related options

        if self.proxy:
            proxy = self.proxy
            # If the proxy is socks5, change the streamlink proxy parameter to socks5h to prevent some streams from failing to load
            if "socks" in proxy:
                proxy = proxy.replace("://", "h://")
            session.set_option("http-proxy", proxy)
        if self.headers:
            session.set_option("http-headers", self.headers)
        if self.cookies:
            session.set_option("http-cookies", self.cookies)
        return session

    def get_channel_name(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                logutil.error(self.flag, f"Page not found: {response.url}")
                return ""

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            content = response_json["content"]
            if not content:
                logutil.error(self.flag, "Cannot find channel information.")
                return ""

            channel_name = content["channel"]["channelName"]
            if not channel_name:
                logutil.error(self.flag, "Cannot find channel name.")
                return ""

            return channel_name

        except Exception as e:
            logutil.error(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    def get_title(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                logutil.error(self.flag, f"Page not found: {response.url}")
                return ""

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            content = response_json["content"]
            if not content:
                logutil.error(self.flag, "Cannot find channel information.")
                return ""

            title = content["liveTitle"].rstrip()
            if not title:
                logutil.error(self.flag, "Cannot find title.")
                return ""

            return title

        except Exception as e:
            logutil.error(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    def get_status(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                logutil.error(self.flag, f"Page not found: {response.url}")
                return ""

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            status = response_json["content"]["status"]
            if not status:
                logutil.error(self.flag, "Cannot find channel status.")
                return ""

            return status

        except Exception as e:
            logutil.info(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    def get_filename(self, channel_name, title, format):
        live_time = time.strftime("%Y.%m.%d %H.%M.%S")
        # Convert special characters in the filename to full-width characters
        char_dict = {
            '"': "＂",
            "*": "＊",
            ":": "：",
            "<": "＜",
            ">": "＞",
            "?": "？",
            "/": "／",
            "\\": "＼",
            "|": "｜",
        }
        for half, full in char_dict.items():
            title = title.replace(half, full)

        logutil.debug(self.flag, f"live_time: {live_time}")
        logutil.debug(self.flag, f"flag: {self.flag}")
        logutil.debug(self.flag, f"title: {title}")
        logutil.debug(self.flag, f"format: {format}")

        filename = f"[{live_time}]{self.flag}{title[:50]}.{format}"
        return filename

    def get_adult_info(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                logutil.error(self.flag, f"Page not found: {response.url}")
                return ""

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            content = response_json["content"]
            if not content:
                logutil.error(self.flag, "Cannot find channel status.")
                return ""

            adult = content["adult"]
            if not adult:
                logutil.error(self.flag, "Cannot find adult status.")
                return ""

            return adult
        except Exception as e:
            logutil.info(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    def get_user_adult_status(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                logutil.error(self.flag, f"Page not found: {response.url}")
                return ""

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            content = response_json["content"]
            if not content:
                logutil.error(self.flag, "Cannot find channel status.")
                return ""

            user_adult_status = content["userAdultStatus"]
            if not user_adult_status:
                logutil.error(self.flag, "Cannot find user adult status.")
                return ""

            return user_adult_status

        except Exception as e:
            logutil.info(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    # def auto_convert_mp4(self, file_path):
    #     base, _ = os.path.splitext(file_path)
    #     file_path_mp4 = f"{base}.mp4"

    #     logutil.info(self.flag, f"Converting {file_path} to MP4...")
    #     try:
    #         # Convert the file with copying codecs
    #         (ffmpeg.input(file_path).output(file_path_mp4, format="mp4", vcodec="copy", acodec="copy").run(overwrite_output=True, quiet=True))
    #         logutil.info(self.flag, f"Converted {file_path} to {file_path_mp4}")
    #         os.remove(file_path)
    #     except ffmpeg.Error as e:
    #         logutil.info(self.flag, f"Error: {e.stderr.decode('utf-8')}")
    #         os.remove(file_path_mp4)
    #         return

    #     logutil.info(self.flag, f"Conversion successful: {file_path} -> {file_path_mp4}")

    async def download_stream(self, channel_id, output_file):
        url = f"https://chzzk.naver.com/live/{channel_id}"
        stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]

        if not stream:
            logutil.error(self.flag, "Cannot find any streams.")
            return

        with stream.open() as fd:
            process = ffmpeg.input("pipe:0").output(output_file, vcodec="copy", acodec="copy").run_async(pipe_stdin=True, overwrite_output=True)
            logutil.info(self.flag, f"Recording to {output_file}...")
            try:
                while True:
                    data = fd.read(1024)
                    if not data:
                        break
                    process.stdin.write(data)
            except KeyboardInterrupt:
                logutil.warning(self.flag, "KeyboardInterrupt received. Stopping the recording...")
                raise
            finally:
                process.stdin.close()
                process.wait()
                # self.auto_convert_mp4(output_file)

    def print_info(self):
        logutil.info(self.flag, "=============================")
        logutil.info(self.flag, f"platform: {self.platform}")
        logutil.info(self.flag, f"id: {self.id}")
        logutil.info(self.flag, f"name: {self.name}")
        logutil.info(self.flag, f"interval: {self.interval}")
        logutil.info(self.flag, f"headers: {self.headers}")
        logutil.info(self.flag, f"cookies: {self.cookies}")
        logutil.info(self.flag, f"format: {self.format}")
        logutil.info(self.flag, f"proxy: {self.proxy}")
        logutil.info(self.flag, f"output: {self.output}")
        logutil.info(self.flag, "=============================")

    async def run(self):
        if not self.id:
            return

        self.print_info()

        if not os.path.exists(self.output):
            os.makedirs(self.output)

        try:
            status = self.get_status(self.id)
            if status == "OPEN":
                logutil.info(self.flag, "The channel is on air.")

                title = self.get_title(self.id)
                file_name = self.get_filename(self.name, title, self.format)
                output_path = os.path.join(self.output, file_name)

                logutil.debug(self.flag, f"channel_name: {self.name}")
                logutil.debug(self.flag, f"title: {title}")
                logutil.debug(self.flag, f"output_path: {output_path}")

                adult = self.get_adult_info(self.id)
                user_adult_status = self.get_user_adult_status(self.id)

                logutil.debug(self.flag, f"adult: {adult}")
                logutil.debug(self.flag, f"user_adult_status: {user_adult_status}")

                # Perform the stream download asynchronously
                await self.download_stream(self.id, output_path)
            else:
                logutil.info(self.flag, "The channel is offline.")
        except streamlink.exceptions.PluginError as e:
            logutil.error(self.flag, f"Streamlink plugin error: {e}")
        except requests.exceptions.RequestException as e:
            logutil.error(self.flag, f"HTTP request error: {e}")
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
        except KeyboardInterrupt:
            logutil.warning(self.flag, "Stopped by keyboard interrupt.")
            sys.exit(0)
