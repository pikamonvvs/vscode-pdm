import asyncio
import os
import re
import time
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict, Tuple, Union

import anyio
import ffmpeg
import httpx
import streamlink
from httpx_socks import AsyncProxyTransport
from streamlink import NoPluginError
from streamlink.stream import HTTPStream, StreamIO
from streamlink_cli.main import open_stream
from streamlink_cli.output import FileOutput
from streamlink_cli.streamrunner import StreamRunner

from utils.utils import logutil

DEFAULT_INTERVAL = 10
DEFAULT_HEADERS = {"User-Agent": "Chrome"}
DEFAULT_OUTPUT = "output"
DEFAULT_FORMAT = "ts"

recording: Dict[str, Tuple[StreamIO, FileOutput]] = {}


class LiveRecorder:
    def __init__(self, user: dict):
        self.id = user["id"]
        self.platform = user["platform"]
        self.name = user.get("name", self.id)
        self.flag = f"[{self.platform}][{self.name}]"

        self.interval = user.get("interval", DEFAULT_INTERVAL)
        self.headers = user.get("headers", DEFAULT_HEADERS)
        self.cookies = user.get("cookies")
        self.format = user.get("format", DEFAULT_FORMAT)
        self.proxy = user.get("proxy")
        self.output = user.get("output", DEFAULT_OUTPUT)

        self.get_cookies()
        self.client = self.get_client()

    async def start(self):
        self.print_info()

        logutil.info(self.flag, "Checking live stream status")
        while True:
            try:
                await self.run()
                await asyncio.sleep(self.interval)
            except ConnectionError as error:
                if "Protocol error in live stream detection request" not in str(error):
                    logutil.error(self.flag, error)
                await self.client.aclose()
                self.client = self.get_client()
            except NoPluginError as error:
                logutil.error(self.flag, f"NoPluginError: {repr(error)}")
            except Exception as error:
                logutil.error(self.flag, f"Error in live stream detection\n{repr(error)}")

    async def run(self):
        pass

    async def request(self, method, url, **kwargs):
        try:
            response = await self.client.request(method, url, **kwargs)
            return response
        except httpx.ProtocolError as error:
            raise ConnectionError(f"{self.flag}Protocol error in live stream detection request\n{error}")
        except httpx.HTTPError as error:
            raise ConnectionError(f"{self.flag}Error in live stream detection request\n{repr(error)}")
        except anyio.EndOfStream as error:
            raise ConnectionError(f"{self.flag}Proxy error in live stream detection\n{error}")

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

    def get_filename(self, title, format):
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
        filename = f"[{live_time}]{self.flag}{title[:50]}.{format}"
        return filename

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

    def run_record(self, stream: Union[StreamIO, HTTPStream], url, title, format):
        # Get the output filename
        filename = self.get_filename(title, format)
        if stream:
            logutil.info(self.flag, f"Started recording: {filename}")
            # Call streamlink to record the live stream
            result = self.stream_writer(stream, url, filename)
            # If recording is successful and format is specified and not equal to the default platform format, run ffmpeg
            if result and self.format and self.format != format:
                self.run_ffmpeg(filename, format)
            recording.pop(url, None)
            logutil.info(self.flag, f"Stopped recording: {filename}")
        else:
            logutil.error(self.flag, f"No available live stream: {filename}")

    def stream_writer(self, stream, url, filename):
        logutil.info(self.flag, f"Obtained live stream link: {filename}\n{stream.url}")
        output = FileOutput(Path(f"{self.output}/{filename}"))
        try:
            stream_fd, prebuffer = open_stream(stream)
            output.open()
            recording[url] = (stream_fd, output)
            logutil.info(self.flag, f"Recording in progress: {filename}")
            StreamRunner(stream_fd, output, show_progress=True).run(prebuffer)
            return True
        except Exception as error:
            if "timeout" in str(error):
                logutil.warning(self.flag, f"Live stream recording timeout. Please check if the streamer is live or if the network connection is stable: {filename}\n{error}")
            elif re.search("(Unable to open URL|No data returned from stream)", str(error)):
                logutil.warning(self.flag, f"Error opening live stream. Please check if the streamer is live: {filename}\n{error}")
            else:
                logutil.error(self.flag, f"Error recording live stream: {filename}\n{error}")
        finally:
            output.close()

    def run_ffmpeg(self, filename, format):
        logutil.info(self.flag, f"Starting ffmpeg processing: {filename}")
        new_filename = filename.replace(f".{format}", f".{self.format}")
        ffmpeg.input(f"{self.output}/{filename}").output(
            f"{self.output}/{new_filename}",
            codec="copy",
            map_metadata="-1",
            movflags="faststart",
        ).global_args("-hide_banner").run()
        os.remove(f"{self.output}/{filename}")

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


class Afreeca(LiveRecorder):
    async def run(self):
        url = f"https://play.afreecatv.com/{self.id}"
        if url not in recording:
            response = (
                await self.request(
                    method="POST",
                    url="https://live.afreecatv.com/afreeca/player_live_api.php",
                    data={"bid": self.id},
                )
            ).json()
            if response["CHANNEL"]["RESULT"] != 0:
                title = response["CHANNEL"]["TITLE"]
                stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]
                await asyncio.to_thread(self.run_record, stream, url, title, self.format)
