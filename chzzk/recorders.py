# import asyncio
# import json
import os
import re
import time
from http.cookies import SimpleCookie

import httpx
import requests
import streamlink
from httpx_socks import AsyncProxyTransport
from loguru import logger

import ffmpeg

DEFAULT_INTERVAL = 10
DEFAULT_HEADERS = {"User-Agent": "Chrome"}
DEFAULT_OUTPUT = "output"
DEFAULT_FORMAT = "ts"


class Chzzk:
    def __init__(self, user: dict):
        self.platform = user["platform"]
        self.id = user["id"]

        self.name = user.get("name", self.id)
        self.interval = user.get("interval", DEFAULT_INTERVAL)
        self.headers = user.get("headers", DEFAULT_HEADERS)
        self.cookies = user.get("cookies")
        self.format = user.get("format", DEFAULT_FORMAT)
        self.proxy = user.get("proxy")
        self.output = user.get("output", DEFAULT_OUTPUT)

        self.flag = f"[{self.platform}][{self.name}]"

        self.get_ids()
        self.get_cookies()
        self.client = self.get_client()

        logger.debug(f"platform: {self.platform}")
        logger.debug(f"name: {self.name}")
        logger.debug(f"flag: {self.flag}")

    def get_id_from_name(self, name):
        try:
            logger.debug(f"Searching for channel: {name}")
            response = requests.get(f"https://api.chzzk.naver.com/service/v1/search/channels?keyword={name}&size=10", headers=self.headers)
            if response.status_code == 404:
                logger.error(f"Page not found: {response.url}")
                return None

            response_json = response.json()
            # logger.debug(f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            data = response_json["content"]["data"]
            if not data:
                logger.error(f"Cannot find channel {name}.")
                return None

            for channel in data:
                channel_name = channel["channel"]["channelName"]
                if channel_name == name:
                    channel_id = channel["channel"]["channelId"]
                    if not channel_id:
                        logger.error("Cannot find channel ID.")
                        return None
                    return channel_id

        except Exception as e:
            logger.error(f"Error occurred while fetching channel information: {e}")
            return None

        logger.error(f"Cannot find channel {name}.")
        return None

    def get_ids(self):
        if not self.check_if_id(self.id):
            channel_name = self.id
            channel_id = self.get_id_from_name(channel_name)
            if channel_id is None:
                logger.error(f"Cannot find channel ID for name {self.id}.")
                return
            self.id = channel_id
            if self.name == self.id:
                self.name = channel_name
        else:
            channel_name, _ = self.get_channel_info(self.id)
            if channel_name is None:
                logger.error(f"Cannot find channel name for ID {self.id}.")
                return
            self.name = channel_name

    def check_if_id(self, channel):
        # check if the string is a valid channel id
        pattern = re.compile(r"^[0-9a-f]{32}$")
        return bool(pattern.match(channel))

    def get_cookies(self):
        if self.cookies:
            cookies = SimpleCookie()
            cookies.load(self.cookies)
            self.cookies = {k: v.value for k, v in cookies.items()}

    def get_cookies_from_file(self):
        current_script_dir = os.getcwd()
        plugins_dir = os.path.join(current_script_dir, "plugins")

        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)

        cookies_file_path = os.path.join(plugins_dir, "cookies.txt")

        if not os.path.isfile(cookies_file_path) or os.path.getsize(cookies_file_path) == 0:
            logger.warning("The cookies.txt file does not exist or is empty. Please enter the cookie values.")
            logger.warning("\nReference: https://github.com/BlackOut-git/Chzzk-live-recorder")
            NID_AUT = input("Enter the NID_AUT cookie value: ")
            NID_SES = input("Enter the NID_SES cookie value: ")
            with open(cookies_file_path, "w") as f:
                f.write(f"NID_AUT={NID_AUT}; NID_SES={NID_SES};")
        else:
            logger.info(f"cookies.txt exists on {cookies_file_path}")

        with open(cookies_file_path, "r") as f:
            return f.read().strip()

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
        session = streamlink.session.Streamlink({"stream-segment-timeout": 60, "hls-segment-queue-threshold": 10})
        # Add streamlink's HTTP related options
        if proxy := self.proxy:
            # If the proxy is socks5, change the streamlink proxy parameter to socks5h to prevent some streams from failing to load
            if "socks" in proxy:
                proxy = proxy.replace("://", "h://")
            session.set_option("http-proxy", proxy)
        if self.headers:
            session.set_option("http-headers", self.headers)
        if self.cookies:
            session.set_option("http-cookies", self.cookies)
        return session

    def get_channel_info(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                logger.error(f"Page not found: {response.url}")
                return None

            response_json = response.json()
            # logger.debug(f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            content = response_json["content"]
            if not content:
                logger.error("Cannot find channel information.")
                return None

            channel_name = content["channel"]["channelName"]
            if not channel_name:
                logger.error("Cannot find channel name.")
                return None

            title = content["liveTitle"].rstrip()
            if not title:
                logger.error("Cannot find title.")
                return None

            return channel_name, title

        except Exception as e:
            logger.error(f"Error occurred while fetching channel information: {e}")
            return None

        logger.error("Cannot find channel information.")
        return None

    def get_status(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                return None

            response_json = response.json()
            # logger.debug(f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            status = response_json["content"]["status"]
            if not status:
                logger.error("Cannot find channel status.")
                return None

            return status

        except Exception as e:
            logger.info(self.flag, f"Error occurred while fetching channel information: {e}")
            return None

        return None

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

        logger.debug(f"live_time: {live_time}")
        logger.debug(f"flag: {self.flag}")
        logger.debug(f"title: {title}")
        logger.debug(f"format: {format}")

        filename = f"[{live_time}]{self.flag}{title[:50]}.{format}"
        return filename

    def auto_convert_mp4(self, file_path):
        base, _ = os.path.splitext(file_path)
        file_path_mp4 = f"{base}.mp4"

        logger.info(self.flag, f"Converting {file_path} to MP4...")
        try:
            # Convert the file with copying codecs
            (ffmpeg.input(file_path).output(file_path_mp4, format="mp4", vcodec="copy", acodec="copy").run(overwrite_output=True, quiet=True))
            logger.info(self.flag, f"Converted {file_path} to {file_path_mp4}")
            os.remove(file_path)
        except ffmpeg.Error as e:
            logger.info(self.flag, f"Error: {e.stderr.decode('utf-8')}")
            os.remove(file_path_mp4)
            return

        logger.info(self.flag, f"Conversion successful: {file_path} -> {file_path_mp4}")

    def download_stream(self, channel_id, output_file):
        url = f"https://chzzk.naver.com/live/{channel_id}"
        stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]

        if not stream:
            logger.error(self.flag, "Cannot find any streams.")
            return

        with stream.open() as fd:
            process = ffmpeg.input("pipe:0").output(output_file, vcodec="copy", acodec="copy").run_async(pipe_stdin=True, overwrite_output=True)
            logger.info(self.flag, f"Recording to {output_file}...")
            try:
                while True:
                    data = fd.read(1024)
                    if not data:
                        break
                    process.stdin.write(data)
            except KeyboardInterrupt:
                logger.warning(self.flag, "KeyboardInterrupt received. Stopping the recording...")
            finally:
                process.stdin.close()
                process.wait()
                self.auto_convert_mp4(output_file)

    def print_info(self):
        logger.info("=============================")
        logger.info(f"platform: {self.platform}")
        logger.info(f"id: {self.id}")
        logger.info(f"name: {self.name}")
        logger.info(f"interval: {self.interval}")
        logger.info(f"headers: {self.headers}")
        logger.info(f"cookies: {self.cookies}")
        logger.info(f"format: {self.format}")
        logger.info(f"proxy: {self.proxy}")
        logger.info(f"output: {self.output}")
        logger.info("=============================")

    def run(self):
        if not self.id:
            logger.error("Cannot find channel ID.")
            return

        self.print_info()

        if not os.path.exists(self.output):
            os.makedirs(self.output)

        while True:
            status = self.get_status(self.id)
            logger.debug(self.flag, f"status: {status}")
            if status == "OPEN":
                logger.info("The channel is on air.")

                _, title = self.get_channel_info(self.id)
                file_name = self.get_filename(self.name, title, self.format)
                output_path = os.path.join(self.output, file_name)

                logger.debug(self.flag, f"channel_name: {self.name}")
                logger.debug(self.flag, f"title: {title}")
                logger.debug(self.flag, f"output_path: {output_path}")

                self.download_stream(self.id, output_path)
            else:
                logger.info(self.flag, f"The channel is offline. Checking again in {self.interval} seconds.")
                time.sleep(self.interval)
