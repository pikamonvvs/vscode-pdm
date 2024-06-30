import os
import re
import shutil
import subprocess
import zipfile

import requests
from bs4 import BeautifulSoup
from logutil import LogUtil as Logger

import ffmpeg


class FfmpegInstaller:
    def __init__(self):
        self.cur_dir = os.getcwd()
        self.ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        self.ffmpeg_dir = os.path.join(self.cur_dir, "ffmpeg")
        self.ffmpeg_zip = os.path.join(self.cur_dir, "ffmpeg-release-essentials.zip")
        self.ffmpeg_bin = os.path.join(self.ffmpeg_dir, "bin")
        self.ffmpeg_exe = os.path.join(self.ffmpeg_bin, "ffmpeg.exe")

        self.logger = Logger()

        self.logger.log_debug(f"ffmpeg_url: {self.ffmpeg_url}")
        self.logger.log_debug(f"ffmpeg_dir: {self.ffmpeg_dir}")
        self.logger.log_debug(f"ffmpeg_zip: {self.ffmpeg_zip}")
        self.logger.log_debug(f"ffmpeg_bin: {self.ffmpeg_bin}")

    def check_ffmpeg_installed(self):
        return os.path.exists(self.ffmpeg_exe)

    def install_ffmpeg(self):
        # Download FFmpeg
        self.logger.log_info("Downloading ffmpeg...")
        response = requests.get(self.ffmpeg_url)
        with open(self.ffmpeg_zip, "wb") as f:
            f.write(response.content)
        self.logger.log_info("FFmpeg is downloaded")

        # Extract FFmpeg
        self.logger.log_info("Extracting ffmpeg...")
        with zipfile.ZipFile(self.ffmpeg_zip, "r") as zip_ref:
            zip_ref.extractall(self.cur_dir)
            extracted_folder_name = zip_ref.namelist()[0].split("/")[0]
            self.logger.log_info(f"Extracted folder name: {extracted_folder_name}")
        self.logger.log_info("FFmpeg is extracted")

        # Remove the previous folder if exists to prevent conflicts
        if os.path.exists(self.ffmpeg_dir):
            shutil.rmtree(self.ffmpeg_dir)

        # Rename extracted folder to ffmpeg
        os.rename(os.path.join(self.cur_dir, extracted_folder_name), self.ffmpeg_dir)
        self.logger.log_info(f"Renamed '{extracted_folder_name}' to '{self.ffmpeg_dir}'")

        # Remove FFmpeg zip file
        self.logger.log_info("Removing ffmpeg zip file...")
        os.remove(self.ffmpeg_zip)
        self.logger.log_info("FFmpeg zip file is removed")

    def register_ffmpeg_to_path(self):
        self.logger.log_info("Registering ffmpeg to PATH...")
        env_path = os.environ.get("PATH", "")
        self.logger.log_debug(f"Current PATH: {env_path}")
        env_path = self.ffmpeg_bin + os.pathsep + env_path
        os.environ["PATH"] = env_path
        self.logger.log_debug(f"New PATH: {os.environ.get('PATH')}")
        self.logger.log_info("FFmpeg is registered to PATH")

    def get_current_version(self):
        try:
            result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            version_info = result.stdout.split("\n")[0].split()[2]
            self.logger.log_debug(f"version_info = {version_info}")
            match = re.search(r"\d+\.\d+\.\d+", version_info)
            if not match:
                self.logger.log_error("Cannot find version")
                return None
            version = match.group()
            self.logger.log_debug(f"version: {version}")
            return version
        except Exception as e:
            return f"An error occurred: {e}"

    def get_latest_version(self):
        try:
            url = "https://www.gyan.dev/ffmpeg/builds/"
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            release_span = soup.find("span", id="release-version")
            if not release_span:
                return "Latest release version not found"
                return None

            version = release_span.text.strip()
            self.logger.log_debug(f"version: {version}")
            return version
        except Exception as e:
            return f"An error occurred: {e}"

    def check_using_older_version(self, version1, version2):
        v1_parts = list(map(int, version1.split(".")))
        v2_parts = list(map(int, version2.split(".")))

        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return True

        return False

    def update_ffmpeg(self):
        local_version = self.get_current_version()
        remote_version = self.get_latest_version()

        is_older_version = self.check_using_older_version(local_version, remote_version)
        if is_older_version:
            self.logger.log_info("An older version is being used.")
            self.logger.log_info("Download newer version...")
            self.install_ffmpeg()
        else:
            self.logger.log_info("The latest version is being used.")

    def test_ffmpeg(self):
        self.logger.log_info("Checking FFmpeg version...")
        try:
            result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            version_info = result.stdout
            self.logger.log_info(f"FFmpeg version: {version_info}")
        except Exception as e:
            self.logger.log_exception(f"Error: {e}")
            raise e
        self.logger.log_info("FFmpeg version is checked")

        self.logger.log_info("Testing ffmpeg-python...")
        try:
            (ffmpeg.input("testsrc=size=640x360:rate=30", f="lavfi", t=1).output("null", f="null").run(quiet=True))
            self.logger.log_info("ffmpeg-python is working correctly.")
        except ffmpeg.Error as e:
            self.logger.log_exception(f"Error: {e.stderr.decode('utf-8')}")
            raise e
        self.logger.log_info("ffmpeg-python is tested")

    def run(self):
        if not self.check_ffmpeg_installed():
            self.install_ffmpeg()
        else:
            self.logger.log_info("FFmpeg is already installed")
        self.register_ffmpeg_to_path()
        self.test_ffmpeg()


def test():
    installer = FfmpegInstaller()
    installer.install_ffmpeg()
    installer.install_ffmpeg()


def main():
    installer = FfmpegInstaller()
    installer.run()


if __name__ == "__main__":
    main()
    # test()
