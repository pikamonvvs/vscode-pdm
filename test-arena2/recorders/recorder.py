import asyncio
import os
import re
import time
from abc import ABC, abstractmethod
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict, Tuple, Union

import aiohttp
import ffmpeg
import httpx
import streamlink
from anyio import EndOfStream
from httpx import HTTPError, ProtocolError
from httpx_socks import AsyncProxyTransport
from requests.exceptions import ConnectionError, RequestException, SSLError
from streamlink import NoPluginError, PluginError
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
                # await self.run()
                await asyncio.sleep(self.interval)
            except ConnectionError as e:
                if "Protocol error in live stream detection request" not in str(e):
                    logutil.error(self.flag, e)
                await self.client.aclose()
                self.client = self.get_client()
            except PluginError as e:
                logutil.error(self.flag, f"Streamlink plugin error: {e}")
            except NoPluginError as e:
                logutil.error(self.flag, f"NoPluginError: {e}")
            except PermissionError as e:
                logutil.error(self.flag, f"Permission error: {e}")
                time.sleep(self.interval)
            except RequestException as e:
                logutil.error(self.flag, f"HTTP request error: {e}")
                time.sleep(self.interval)
            except KeyboardInterrupt:
                logutil.warning(self.flag, "Stopped by keyboard interrupt.")
                raise
            except Exception as e:
                logutil.error(self.flag, f"Error in live stream detection: {e}")

    @abstractmethod
    async def run(self):
        pass

    async def request(self, method, url, **kwargs):
        try:
            response = await self.client.request(method, url, **kwargs)
            return response
        except ProtocolError as e:
            logutil.error(self.flag, f"Protocol error: {e}")
            raise e
        except HTTPError as e:
            logutil.error(self.flag, f"HTTP error: {e}")
            raise e
        except EndOfStream as e:
            logutil.error(self.flag, f"End of stream: {e}")
            raise e
        except SSLError as e:
            logutil.error(self.flag, f"SSL error: {e}")
            raise e
        except ConnectionError as e:
            logutil.error(self.flag, f"Connection error: {e}")
            raise e
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
        try:
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
        except Exception as e:
            logutil.error(self.flag, f"Unexpected error: {e}")
            raise e


class Chzzk(LiveRecorder):
    def __init__(self, user: dict):
        super().__init__(user)
        self.get_ids()
        self.flag = f"[{self.platform}][{self.name}]"

    async def run(self):
        try:
            status = await self.get_status(self.id)
            # logutil.debug(self.flag, f"status: {status}")
            if status == "OPEN":
                logutil.info(self.flag, "The channel is on air.")

                title = await self.get_title(self.id)
                file_name = await self.get_filename(title, self.format)
                output_path = os.path.join(self.output, file_name)
                adult = await self.get_adult_info(self.id)
                user_adult_status = await self.get_user_adult_status(self.id)

                logutil.debug(self.flag, f"channel_name: {self.name}")
                logutil.debug(self.flag, f"title: {title}")
                logutil.debug(self.flag, f"output_path: {output_path}")
                logutil.debug(self.flag, f"adult: {adult}")
                logutil.debug(self.flag, f"user_adult_status: {user_adult_status}")

                await self.download_stream(self.id, output_path)
            else:
                logutil.info(self.flag, "The channel is offline.")
                await asyncio.sleep(self.interval)
        except Exception as e:
            logutil.error(self.flag, f"Error occurred while running the recorder: {e}")
            raise e

    async def check_if_id(self, channel):
        # check if the string is a valid channel id
        pattern = re.compile(r"^[0-9a-f]{32}$")
        return bool(pattern.match(channel))

    async def fetch_value(url, keys, headers=None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logutil.error(f"Failed to load the page. Status code: {response.status}")
                        return None
                    if not response.content:
                        logutil.error("Response content is empty.")
                        return None
                    response_json = await response.json()
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
        data = await self.fetch_value(url, ["content", "data"], headers=self.headers)
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
        channel_name = await self.fetch_value(url, ["content", "channel", "channelName"], headers=self.headers)
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

    async def get_status(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        status = await self.fetch_value(url, ["content", "status"], headers=self.headers)
        if status is None:
            logutil.error(f"{self.flag}: Cannot find channel status.")
            return ""
        return status

    async def get_title(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        title = await self.fetch_value(url, ["content", "liveTitle"], headers=self.headers)
        if title is None:
            logutil.error(f"{self.flag}: Cannot find title.")
            return ""
        return title.rstrip()

    async def get_adult_info(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        adult_info = await self.fetch_value(url, ["content", "adult"], headers=self.headers)
        if adult_info is None:
            logutil.error(f"{self.flag}: Cannot find adult info.")
            return ""
        return adult_info

    async def get_user_adult_status(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        user_adult_status = await self.fetch_value(url, ["content", "userAdultStatus"], headers=self.headers)
        if user_adult_status is None:
            logutil.error(f"{self.flag}: Cannot find user adult status.")
            return ""
        return user_adult_status

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

        async with aiohttp.ClientSession() as session:
            async with session.get(stream.url) as response:
                if response.status != 200:
                    logutil.error(self.flag, f"Failed to open stream: {response.status}")
                    return

                process = ffmpeg.input("pipe:0").output(output_file, vcodec="copy", acodec="copy").run_async(pipe_stdin=True, overwrite_output=True)
                logutil.info(self.flag, f"Recording to {output_file}...")

                try:
                    while True:
                        data = await response.content.read(1024)
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
