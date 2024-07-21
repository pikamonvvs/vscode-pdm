import asyncio

from recorders.recorder import LiveRecorder, recording


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
