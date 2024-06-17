import os
import subprocess
import zipfile

import requests

import ffmpeg
from classes.logutil import LogUtil as Logger


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
    print(installer.check_ffmpeg_installed())


def main():
    installer = FfmpegInstaller()
    installer.run()


if __name__ == "__main__":
    main()
