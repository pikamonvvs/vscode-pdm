import asyncio
import json
import os
import re
import time
from abc import ABC, abstractmethod
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict, Tuple

import ffmpeg
import httpx
import streamlink
from anyio import EndOfStream
from bs4 import BeautifulSoup
from httpx import HTTPError, ProtocolError
from httpx_socks import AsyncProxyTransport
from requests.exceptions import ConnectionError, SSLError
from streamlink.stream import StreamIO
from streamlink_cli.main import open_stream
from streamlink_cli.output import FileOutput
from streamlink_cli.streamrunner import StreamRunner

import utils.config as config
from utils.utils import logutil

recording: Dict[str, Tuple[StreamIO, FileOutput]] = {}


class LiveRecorder(ABC):
    def __init__(self, user: dict):
        # Parse required arguments
        self.platform = user.get(config.KEY_PLATFORM)
        self.id = user.get(config.KEY_ID)
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
            except ConnectionError as e:
                logutil.error(self.flag, e)
                await self.client.aclose()
                self.client = self.get_client()
                await asyncio.sleep(self.interval)
            except KeyboardInterrupt:
                logutil.warning(self.flag, "Stopped by keyboard interrupt.")
                break
            except Exception as e:
                logutil.error(self.flag, f"Error in live stream detection: {e}")
                await asyncio.sleep(self.interval)

    @abstractmethod
    async def run(self):
        pass

    async def request(self, method, url, **kwargs):
        try:
            response = await self.client.request(method, url, **kwargs)
            if response.status_code != 200:
                logutil.error(f"Failed to load the page. Status code: {response.status_code}")
                return None
            if not response.content:
                logutil.error("Response content is empty.")
                return None
            return response
        except (ConnectionError, ProtocolError, HTTPError, EndOfStream, SSLError) as e:
            logutil.error(self.flag, f"Connection error: {e}")
            raise ConnectionError
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e

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

    def get_client2(self):
        http2 = True
        timeout = self.interval
        limits = httpx.Limits(max_keepalive_connections=100, keepalive_expiry=self.interval * 2)
        headers = self.headers
        cookies = self.cookies

        if self.proxy:
            if "socks" in self.proxy:
                transport = AsyncProxyTransport.from_url(self.proxy)
            else:
                proxies = self.proxy

        return httpx.AsyncClient(http2=http2, timeout=timeout, limits=limits, headers=headers, cookies=cookies, proxies=proxies, transport=transport)

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
        try:
            for half, full in char_dict.items():
                title = title.replace(half, full)
            filename = f"[{live_time}]{self.flag}{title[:50]}.{format}"
            return filename
        except Exception as e:
            logutil.error(self.flag, f"Exception occurred: {e}")
            return ""

    def run_record(self, stream, url, title, format):
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
        output = FileOutput(Path(os.path.join(self.output, filename)))
        try:
            stream_fd, prebuffer = open_stream(stream)
            output.open()
            recording[url] = (stream_fd, output)
            logutil.info(self.flag, f"Recording in progress: {filename}")
            StreamRunner(stream_fd, output, show_progress=True).run(prebuffer)
            return True
        except Exception as e:
            if "timeout" in str(e):
                logutil.warning(self.flag, f"Live stream recording timeout. Please check if the streamer is live or if the network connection is stable: {filename}\n{e}")
            elif re.search("(Unable to open URL|No data returned from stream)", str(e)):
                logutil.warning(self.flag, f"Error opening live stream. Please check if the streamer is live: {filename}\n{e}")
            else:
                logutil.error(self.flag, f"Error recording live stream: {filename}\n{e}")
        finally:
            output.close()

    def run_ffmpeg(self, filename, format):
        logutil.info(self.flag, f"Starting ffmpeg processing: {filename}")
        new_filename = filename.replace(f".{format}", f".{self.format}")
        input_path = os.path.join(self.output, filename)
        output_path = os.path.join(self.output, new_filename)
        ffmpeg.input(input_path).output(output_path, codec="copy", map_metadata="-1", movflags="faststart", reset_timestamps=1).global_args("-hide_banner").run()  # Add option for resetting timestamp
        os.remove(input_path)

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
        try:
            if url not in recording:
                response = (
                    await self.request(
                        method="POST",
                        url="https://live.afreecatv.com/afreeca/player_live_api.php",
                        data={"bid": self.id},
                    )
                ).json()
                status = response.get("CHANNEL", {}).get("RESULT")
                if status != 0:
                    logutil.info(self.flag, "The channel is on air.")
                    title = response.get("CHANNEL", {}).get("TITLE")
                    stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]
                    await asyncio.to_thread(self.run_record, stream, url, title, self.format)
                else:
                    logutil.info(self.flag, "The channel is offline.")
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e


class Chzzk(LiveRecorder):
    async def start(self):
        await self.get_ids()
        self.flag = f"[{self.platform}][{self.name}]"
        await super().start()

    async def run(self):
        url = f"https://chzzk.naver.com/live/{self.id}"
        try:
            if url not in recording:
                response = (
                    await self.request(
                        method="GET",
                        url=f"https://api.chzzk.naver.com/service/v2/channels/{self.id}/live-detail",
                    )
                ).json()
                status = response.get("content", {}).get("status")
                if status == "OPEN":
                    logutil.info(self.flag, "The channel is on air.")
                    title = response.get("content", {}).get("liveTitle").rstrip()
                    stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]
                    await asyncio.to_thread(self.run_record, stream, url, title, self.format)
                else:
                    logutil.info(self.flag, "The channel is offline.")
        except Exception as e:
            logutil.error(self.flag, f"Error occurred while running the recorder: {e}")
            raise e

    async def check_if_id(self, channel):
        pattern = re.compile(r"^[0-9a-f]{32}$")
        return bool(pattern.match(channel))

    async def fetch_value(self, url, keys):
        try:
            response = await self.request(method="GET", url=url)
            if response.status_code != 200:
                logutil.error(f"Failed to load the page. Status code: {response.status_code}")
                return None
            if not response.content:
                logutil.error("Response content is empty.")
                return None
            response_json = response.json()
            if not response_json:
                logutil.error("Response JSON is None or empty.")
                return None
            data = response_json
            for key in keys:
                if isinstance(data, dict):
                    data = data.get(key)
                    if data is None:
                        logutil.error(f"Key '{key}' not found in the JSON data.")
                        return None
                else:
                    logutil.error(f"Data is not a dictionary at key '{key}'.")
                    return None
            return data
        except Exception as e:
            logutil.error(f"Error occurred while fetching JSON: {e}")
            return None

    async def get_id_from_name(self, name):
        url = f"https://api.chzzk.naver.com/service/v1/search/channels?keyword={name}&size=10"
        data = await self.fetch_value(url, ["content", "data"])
        if data is None:
            logutil.error(f"{self.flag}: Cannot find channel '{name}'.")
            return None

        for channel in data:
            channel_info = channel.get("channel")
            if channel_info is None:
                logutil.error("Invalid response structure: 'channel' key is missing.")
                continue
            channel_name = channel_info.get("channelName")
            if channel_name == name:
                channel_id = channel_info.get("channelId")
                if not channel_id:
                    logutil.error("Cannot find channel ID.")
                    return None
                return channel_id

        logutil.error(f"Cannot find channel '{name}'.")
        return None

    async def get_channel_name(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        channel_name = await self.fetch_value(url, ["content", "channel", "channelName"])
        if channel_name is None:
            logutil.error(f"{self.flag}: Cannot find channel name.")
            return ""
        return channel_name

    async def get_ids(self):
        if not await self.check_if_id(self.id):
            channel_name = self.id
            channel_id = await self.get_id_from_name(channel_name)
            if channel_id is None:
                logutil.error(f"Cannot find channel ID for name {self.id}.")
                return
            self.id = channel_id
            if self.name == self.id:
                self.name = channel_name
        else:
            channel_name = await self.get_channel_name(self.id)
            if channel_name is None:
                logutil.error(f"Cannot find channel name for ID {self.id}.")
                return
            self.name = channel_name


class TikTok(LiveRecorder):
    async def start(self):
        self.flag = f"[{self.platform}][{self.id}]"
        await super().start()

    async def run(self):
        url = f"https://www.tiktok.com/@{self.id}/live"
        try:
            if url not in recording:
                room_id = await self.get_room_id()
                response = (
                    await self.request(
                        method="GET",
                        url=f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}",
                    )
                ).json()
                status = response.get("LiveRoomInfo", {}).get("status")
                if status and status != 4:
                    logutil.info(self.flag, "The channel is on air.")
                    title = await self.get_title(room_id)
                    stream = self.get_streamlink().streams(url).get("best")  # HLSStream[mpegts]
                    await asyncio.to_thread(self.run_record, stream, url, title, self.format)
                else:
                    logutil.info(self.flag, "The channel is offline.")
        except Exception as e:
            logutil.error(self.flag, f"Error occurred while running the recorder: {e}")
            raise e

    async def get_room_id(self) -> str:
        room_id = await self.get_room_id_2()
        if not room_id:
            room_id = await self.get_room_id_1()

        if not room_id:
            logutil.error(self.flag, "Cannot find Room ID.")
            return ""

        return room_id

    async def get_room_id_1(self) -> str:
        url = f"https://www.tiktok.com/@{self.id}/live"
        try:
            response = await self.request(method="GET", url=url)
            match = re.search(r"room_id=(\d+)", response.text)
            if not match:
                logutil.info(self.flag, "Room ID not found")
                return ""
            room_id = match.group(1)
            return room_id

        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            return ""

    async def get_room_id_2(self) -> str:
        url = f"https://www.tiktok.com/@{self.id}"
        try:
            response = await self.request(method="GET", url=url)

            soup = BeautifulSoup(response.text, "html.parser")
            if not soup:
                logutil.error(self.flag, "Failed to parse the page.")
                return ""

            script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
            if not script_tag:
                logutil.error(self.flag, "Cannot find script tag for this ID.")
                return ""

            json_data = json.loads(script_tag.string)
            if not json_data:
                logutil.error(self.flag, "Failed to load JSON data.")
                return ""

            room_id = json_data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {}).get("roomId")
            if not room_id:
                logutil.info(self.flag, "Cannot find Room ID.")
                return ""

            return room_id

        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            return ""

    async def get_title(self, room_id) -> str:
        url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={room_id}"
        try:
            response = await self.request(method="GET", url=url)
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
