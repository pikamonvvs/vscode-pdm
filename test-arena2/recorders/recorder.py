import asyncio
import os
import re
import time
from abc import ABC, abstractmethod
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict, Tuple, Union

import anyio
import ffmpeg
import httpx
import streamlink
from httpx_socks import AsyncProxyTransport
from requests.exceptions import ConnectionError, RequestException
from streamlink.exceptions import NoPluginError, PluginError
from streamlink.stream import HTTPStream, StreamIO
from streamlink_cli.main import open_stream
from streamlink_cli.output import FileOutput
from streamlink_cli.streamrunner import StreamRunner

import utils.config as config
from utils.utils import logutil

recording: Dict[str, Tuple[StreamIO, FileOutput]] = {}


class LiveRecorder(ABC):
    def __init__(self, user: dict):
        # Parse required arguments
        self.platform = user[config.KEY_PLATFORM]
        self.id = user[config.KEY_ID]
        self.name = user.get(config.KEY_NAME, self.id)
        self.flag = f"[{self.platform}][{self.name}]"

        # Parse optional arguments
        self.interval = user.get(config.KEY_INTERVAL, config.DEFAULT_INTERVAL)
        self.headers = user.get(config.KEY_HEADERS, config.DEFAULT_HEADERS)
        self.cookies = user.get(config.KEY_COOKIES)
        self.format = user.get(config.KEY_FORMAT, config.DEFAULT_FORMAT)
        self.proxy = user.get(config.KEY_PROXY)
        self.output = user.get(config.KEY_OUTPUT, config.DEFAULT_OUTPUT)

        # Initialize cookies and client
        self.get_cookies()
        self.client = self.get_client()

    async def start(self):
        if not os.path.exists(self.output):
            os.makedirs(self.output)

        self.print_info()

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
            except PluginError as error:
                logutil.error(self.flag, f"Streamlink plugin error: {repr(error)}")
                time.sleep(self.interval)
            except RequestException as error:
                logutil.error(self.flag, f"HTTP request error: {repr(error)}")
                time.sleep(self.interval)
            except Exception as error:
                logutil.error(self.flag, f"Error in live stream detection: {repr(error)}")

    @abstractmethod
    async def run(self):  # TODO: afreeca에 start랑 run에 나눠져있는 게 chzzk에는 run에 다 구현되어있는데, 어떻게 할지 고민 필요.
        pass

    async def request(self, method, url, **kwargs):  # TODO: afreeca에서 사용되며, 어떻게 쓸지 고민 필요.
        try:
            response = await self.client.request(method, url, **kwargs)
            return response
        except httpx.ProtocolError as error:
            raise ConnectionError(f"{self.flag}Protocol error in live stream detection request\n{error}")
        except httpx.HTTPError as error:
            raise ConnectionError(f"{self.flag}Error in live stream detection request\n{repr(error)}")
        except anyio.EndOfStream as error:
            raise ConnectionError(f"{self.flag}Proxy error in live stream detection\n{error}")

    """@common_function"""

    def is_file(self, file_path):
        return os.path.isfile(file_path)

    """@common_function"""

    def get_cookies(self):
        logutil.info(self.flag, "self.cookies: ", self.cookies)
        if self.cookies:
            cookies = SimpleCookie()
            if self.is_file(self.cookies):
                self.cookies = open(self.cookies, "r").read().strip()
                logutil.info(self.flag, "self.cookies: ", self.cookies)
            cookies.load(self.cookies)
            self.cookies = {k: v.value for k, v in cookies.items()}

    """@common_function"""

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

    """@common_function"""

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

    """@common_function"""

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
