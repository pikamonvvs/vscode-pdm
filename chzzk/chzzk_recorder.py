# import asyncio
import json
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
import utils.utils as utils

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

        logger.debug(f"platform: {self.platform}")
        logger.debug(f"name: {self.name}")
        logger.debug(f"flag: {self.flag}")

        self.get_cookies()
        self.client = self.get_client()

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
            logger.info("The cookies.txt file does not exist or is empty. Please enter the cookie values.")
            logger.info("\nReference: https://github.com/BlackOut-git/Chzzk-live-recorder")
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

    def get_id_from_name(self, name):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v1/search/channels?keyword={name}&size=1", headers=self.headers).json()
            data = response["content"]["data"]
            if not data:
                logger.info(f"Cannot find channel {name}.")
                return None

            for channel in data:
                channel_name = channel["channel"]["channelName"]
                if channel_name == name:
                    return channel["channel"]["channelId"]

        except Exception as e:
            logger.info(f"Error occurred while fetching channel information: {e}")
            return None

        return None

    def get_channel_info(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                return None

            content = response.json()["content"]

            logger.debug(f"content: {json.dumps(content, indent=4, ensure_ascii=False)}")

            channel_name = content["channel"]["channelName"]
            title = content["liveTitle"].rstrip()
            category = content["liveCategoryValue"]

            return channel_name, title, category

        except Exception as e:
            logger.info(f"Error occurred while fetching channel information: {e}")
            return None
        return None

    def check_if_live(self, channel_id):
        try:
            response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
            if response.status_code == 404:
                return None
            data_json = response.json()
            logger.debug(f"channel information: {json.dumps(data_json, indent=4, ensure_ascii=False)}")
            status = data_json["content"]["status"]
            return status
        except Exception as e:
            logger.info(f"Error occurred while fetching channel information: {e}")
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

        logger.info(f"Converting {file_path} to MP4...")
        try:
            # Convert the file with copying codecs
            (ffmpeg.input(file_path).output(file_path_mp4, format="mp4", vcodec="copy", acodec="copy").run(overwrite_output=True, quiet=True))
            logger.info(f"Converted {file_path} to {file_path_mp4}")
            os.remove(file_path)
        except ffmpeg.Error as e:
            logger.info(f"Error: {e.stderr.decode('utf-8')}")
            os.remove(file_path_mp4)
            return

        logger.info(f"Conversion successful: {file_path} -> {file_path_mp4}")

    def download_stream(self, channel_id, output_file):
        url = f"https://chzzk.naver.com/live/{channel_id}"
        stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]

        with stream.open() as fd:
            process = ffmpeg.input("pipe:0").output(output_file, vcodec="copy", acodec="copy").run_async(pipe_stdin=True, overwrite_output=True)
            try:
                while True:
                    data = fd.read(1024)
                    if not data:
                        break
                    process.stdin.write(data)
            except KeyboardInterrupt:
                logger.warning("KeyboardInterrupt")
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
            logger.info("Channel ID or channel name is required.")
            return

        if not self.check_if_id(self.id):
            channel_id = self.get_id_from_name(self.id)
            if channel_id is None:
                logger.info(f"Cannot find channel {self.id}.")
                return
            self.id = channel_id

        self.print_info()

        if not os.path.exists(self.output):
            os.makedirs(self.output)

        while True:
            status = self.check_if_live(channel_id)
            logger.debug(f"status: {status}")
            if status == "OPEN":
                logger.info("The channel is on air.")

                channel_name, title, category = self.get_channel_info(channel_id)
                file_name = self.get_filename(channel_name, title, self.format)
                output_path = os.path.join(self.output, file_name)

                logger.debug(f"channel_name: {channel_name}")
                logger.debug(f"title: {title}")
                logger.debug(f"category: {category}")
                logger.debug(f"output_path: {output_path}")

                self.download_stream(channel_id, output_path)
            else:
                logger.info(f"The channel is offline. Checking again in {self.interval} seconds.")
                time.sleep(self.interval)


def main():
    logger.add(
        sink="logs/log_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="3 days",
        level="INFO",
        encoding="utf-8",
        format="[{time:YYYY-MM-DD HH:mm:ss}][{level}][{name}][{function}:{line}]{message}",
    )
    args = utils.parse_args()
    platform = globals()[args.get("platform")]
    platform(args).run()


if __name__ == "__main__":
    main()
