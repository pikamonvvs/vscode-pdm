import asyncio

import httpx
from loguru import logger as logging


class YourClass:
    def __init__(self, flag, headers):
        self.flag = flag
        self.headers = headers
        self.client = httpx.AsyncClient(http2=True, headers=headers)

    async def fetch_value(url, keys, headers=None):
        try:
            async with httpx.AsyncClient(headers=headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logging.error(f"Failed to load the page. Status code: {response.status_code}")
                    return None
                if not response.content:
                    logging.error("Response content is empty.")
                    return None
                response_json = response.json()
                if not response_json:
                    logging.error("Response JSON is None or empty.")
                    return None
                # 중첩된 키를 따라가며 값을 추출
                data = response_json
                for key in keys:
                    if isinstance(data, dict):
                        data = data.get(key)
                        if data is None:
                            logging.error(f"Key '{key}' not found in the JSON data.")
                            return None
                    else:
                        logging.error(f"Data is not a dictionary at key '{key}'.")
                        return None
                return data
        except Exception as e:
            logging.error(f"Error occurred while fetching JSON: {e}")
            return None

    async def get_id_from_name(self, name):
        url = f"https://api.chzzk.naver.com/service/v1/search/channels?keyword={name}&size=10"
        data = await self.fetch_value(url, ["content", "data"], headers=self.headers)
        if data is None:
            logging.error(f"{self.flag}: Cannot find channel '{name}'.")
            return None

        for channel in data:
            channel_info = channel.get("channel")
            if channel_info is None:
                logging.error("Invalid response structure: 'channel' key is missing.")
                continue
            channel_name = channel_info.get("channelName")
            if channel_name == name:
                channel_id = channel_info.get("channelId")
                if not channel_id:
                    logging.error("Cannot find channel ID.")
                    return None
                return channel_id

        logging.error(f"Cannot find channel '{name}'.")
        return None

    async def get_status(self, channel_id):
        url = f"https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail"
        status = await self.fetch_value(url, ["content", "status"], headers=self.headers)
        if status is None:
            logging.error(f"{self.flag}: Cannot find channel status.")
            return ""
        return status


# 사용 예제
async def main():
    your_instance = YourClass(flag="YourClass", headers={"User-Agent": "Mozilla/5.0"})
    channel_id = await your_instance.get_id_from_name("강지")
    print(f"Channel ID: {channel_id}")
    status = await your_instance.get_status(channel_id)
    print(f"Channel status: {status}")


# 이벤트 루프를 실행하여 main 함수를 실행합니다.

asyncio.run(main())
