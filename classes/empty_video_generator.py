import os
from datetime import datetime

from ffmpeg_installer import FfmpegInstaller

import ffmpeg


class EmptyVideoGenerator:
    def __init__(self):
        self.output_base = "output"
        self.output_prefix = "dummy"

    def get_current_datetime_serial(self):
        # Get the current date and time
        now = datetime.now()
        # Format as "YYYYMMDDHHMMSS"
        serial = now.strftime("%Y%m%d%H%M%S")
        return serial

    def convert_bytes_to_human_readable(self, size, decimal_places=2):
        """Convert a size in bytes to a human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]:
            if size < 1024.0:
                return f"{size:.{decimal_places}f} {unit}"
            size /= 1024.0

    def generate_empty_mp4(self, target_size_mb):
        current_serial = self.get_current_datetime_serial()
        print(f"Current datetime serial: {current_serial}")

        output_file = f"{self.output_prefix}_{current_serial}.mp4"
        output_path = os.path.join(self.output_base, output_file)

        # Create the destination directory if it does not exist
        os.makedirs(self.output_base, exist_ok=True)

        # Generate an empty MP4 file using FFmpeg
        ffmpeg.input("anullsrc", f="lavfi", t=0.1).output(output_path, vcodec="libx264", acodec="aac", f="mp4").run(overwrite_output=True, quiet=True)

        target_size_bytes = target_size_mb * 1024 * 1024
        current_size_bytes = os.path.getsize(output_path)

        if current_size_bytes < target_size_bytes:
            with open(output_path, "ab") as f:
                f.write(b"\0" * (target_size_bytes - current_size_bytes))
        elif current_size_bytes > target_size_bytes:
            raise ValueError("The current file size is larger than the target size. Please set a smaller target size.")

        current_size_bytes = self.convert_bytes_to_human_readable(os.path.getsize(output_path))
        print(f"Generated file size: {current_size_bytes}")
        return output_path

    def is_mp4_file(self, file_path):
        if not os.path.isfile(file_path):
            print("The file does not exist.")
            return False
        try:
            # Use ffprobe to get file information
            probe = ffmpeg.probe(file_path)
            # Check the format name of the file
            format_name = probe["format"]["format_name"]
            # Verify if the format name is one of 'mov,mp4,m4a,3gp,3g2,mj2'
            if "mp4" in format_name.split(","):
                return True
            else:
                return False
        except ffmpeg.Error as e:
            print(f"ffprobe error: {e}")
            return False
        except Exception as e:
            print(f"Other error: {e}")
            return False


def main():
    FfmpegInstaller().run()

    # Get user input
    target_size_mb = int(input("Enter the desired file size in MB: "))

    # Generate an empty MP4 file
    generator = EmptyVideoGenerator()
    output_file = generator.generate_empty_mp4(target_size_mb)

    # Check if the file exists and is an MP4 file
    if generator.is_mp4_file(output_file):
        print("The file is an MP4 file.")
    else:
        print("The file is not an MP4 file.")


if __name__ == "__main__":
    main()
