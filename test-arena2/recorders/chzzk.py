import asyncio
import os
import re

import aiohttp
import ffmpeg
import requests

from recorders.recorder import LiveRecorder
from utils.utils import logutil


class Chzzk(LiveRecorder):
    def __init__(self, user: dict):
        super().__init__(user)
        self.get_ids()
        self.flag = f"[{self.platform}][{self.name}]"

    async def run(self):
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

    def check_if_id(self, channel):
        # check if the string is a valid channel id
        pattern = re.compile(r"^[0-9a-f]{32}$")
        return bool(pattern.match(channel))

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

    def get_channel_name(self, channel_id):
        response = requests.get(f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail", headers=self.headers)
        try:
            if response.status_code == 404:
                logutil.error(self.flag, f"Page not found: {response.url}")
                return ""

            response_json = response.json()
            # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")

            content = response_json.get("content")
            if not content:
                logutil.error(self.flag, "Cannot find channel information.")
                return ""

            channel_name = content.get("channel", {}).get("channelName")
            if not channel_name:
                logutil.error(self.flag, "Cannot find channel name.")
                return ""

            return channel_name

        except Exception as e:
            logutil.error(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    async def get_status(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 404:
                        logutil.error(self.flag, f"Page not found: {response.url}")
                        return ""
                    response_json = await response.json()
                    # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")
                    status = response_json.get("content", {}).get("status")
                    if not status:
                        logutil.error(self.flag, "Cannot find channel status.")
                        return ""
                    return status
        except Exception as e:
            logutil.info(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    async def get_title(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 404:
                        logutil.error(self.flag, f"Page not found: {response.url}")
                        return ""
                    response_json = await response.json()
                    # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")
                    content = response_json.get("content")
                    if not content:
                        logutil.error(self.flag, "Cannot find channel information.")
                        return ""
                    title = content.get("liveTitle", "").rstrip()
                    if not title:
                        logutil.error(self.flag, "Cannot find title.")
                        return ""
                    return title
        except Exception as e:
            logutil.error(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    async def get_adult_info(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 404:
                        logutil.error(self.flag, f"Page not found: {response.url}")
                        return ""
                    response_json = await response.json()
                    # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")
                    content = response_json.get("content")
                    if not content:
                        logutil.error(self.flag, "Cannot find channel status.")
                        return ""
                    adult = content.get("adult")
                    if not adult:
                        logutil.error(self.flag, "Cannot find adult status.")
                        return ""
                    return adult
        except Exception as e:
            logutil.info(self.flag, f"Error occurred while fetching channel information: {e}")
            return ""

    async def get_user_adult_status(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 404:
                        logutil.error(self.flag, f"Page not found: {response.url}")
                        return ""
                    response_json = await response.json()
                    # logutil.debug(self.flag, f"response_json: {json.dumps(response_json, indent=4, ensure_ascii=False)}")
                    content = response_json.get("content")
                    if not content:
                        logutil.error(self.flag, "Cannot find channel status.")
                        return ""
                    user_adult_status = content.get("userAdultStatus")
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
