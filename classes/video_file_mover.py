import ctypes
import os
import platform
import shutil

from ffmpeg_installer import FfmpegInstaller

import ffmpeg


class VideoFileMover:
    def get_drive_free_space(self, drive):
        """Return the free space of the drive in bytes."""
        if platform.system() == "Windows":
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, None, ctypes.pointer(free_bytes))
            return free_bytes.value
        else:
            st = os.statvfs(drive)
            return st.f_bavail * st.f_frsize

    def get_file_allocated_size(self, file_path):
        """Return the allocated size of the file in bytes."""
        if platform.system() == "Windows":
            return os.path.getsize(file_path)
        else:
            st = os.stat(file_path)
            block_size = os.statvfs(file_path).f_frsize
            allocated_size = ((st.st_size + block_size - 1) // block_size) * block_size
            return allocated_size

    def is_file_in_use(self, file_path):
        """Check if a file is currently in use."""
        try:
            os.rename(file_path, file_path)
            return False
        except OSError:
            return True

    def get_files_not_in_use(self, directory):
        """Return a list of files in the given directory (depth 1 only) that are not in use."""
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) and item_path.endswith((".flv", ".mp4", ".ts")) and not self.is_file_in_use(item_path):
                files.append(item_path)
        return files

    def convert_bytes_to_human_readable(self, size, decimal_places=2):
        """Convert a size in bytes to a human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]:
            if size < 1024.0:
                return f"{size:.{decimal_places}f} {unit}"
            size /= 1024.0

    def convert_to_mp4(self, input_file, output_file):
        print(f"Converting {input_file} to MP4...")
        try:
            # Convert the file with copying codecs
            (ffmpeg.input(input_file).output(output_file, format="mp4", vcodec="copy", acodec="copy").run(overwrite_output=True, quiet=True))
            print(f"Converted {input_file} to {output_file}")
        except ffmpeg.Error as e:
            print(f"Error: {e.stderr.decode('utf-8')}")
            raise e

        print(f"Conversion successful: {input_file} -> {output_file}")

    def move_file(self, src_path, dst_path):

        # Create the destination directory if it does not exist
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        try:
            if src_path.endswith(".flv"):
                print("Converting FLV to MP4...")
                dst_path = dst_path.replace(".flv", ".mp4")
                self.convert_to_mp4(src_path, dst_path)
            elif src_path.endswith(".mp4"):
                print("Converting MP4 to MP4...")
                self.convert_to_mp4(src_path, dst_path)
            else:
                print("Moving file...")
                shutil.copy(src_path, dst_path)
        except Exception as e:
            print(f"Error: {e}")
            return False

        print(f"File moved from {src_path} to {dst_path}")
        return True

    def move_files_if_space(self, src_directory, dst_directory, remove_src_files=True):
        # Calculate the total allocated size of files to move
        files_to_move = self.get_files_not_in_use(src_directory)
        total_allocated_size = sum(self.get_file_allocated_size(f) for f in files_to_move)

        # Calculate the free space on the destination drive
        dst_drive = os.path.splitdrive(dst_directory)[0] + os.path.sep
        drive_free_space = self.get_drive_free_space(dst_drive)

        print(f"Total allocated size of files to move: {self.convert_bytes_to_human_readable(total_allocated_size)}")
        print(f"Free space on destination drive: {self.convert_bytes_to_human_readable(drive_free_space)}")

        if total_allocated_size > drive_free_space:
            print(f"Not enough {dst_drive} space on the destination drive to move all files.")
            return

        for src_path in files_to_move:
            dst_path = os.path.join(dst_directory, os.path.relpath(src_path, src_directory))

            is_move_successful = self.move_file(src_path, dst_path)
            if is_move_successful:
                print(f"Moved file from {src_path} to {dst_path}")
                if remove_src_files:
                    print(f"Removing {src_path}...")
                    os.remove(src_path)
                    print(f"Removed {src_path}")
            else:
                print(f"Failed to move file from {src_path} to {dst_path}")
                continue


def main():
    FfmpegInstaller().run()

    src_directory = input("Enter the source directory: ").strip('"')
    if not src_directory:
        src_directory = r"Z:\\"
    dst_directory = input("Enter the destination directory: ").strip('"')
    if not dst_directory:
        dst_directory = r"D:\Works"

    mover = VideoFileMover()
    files_not_in_use = mover.get_files_not_in_use(src_directory)
    total_allocated_size = sum(mover.get_file_allocated_size(f) for f in files_not_in_use)
    drive_free_space = mover.get_drive_free_space(os.path.splitdrive(dst_directory)[0] + os.path.sep)

    print(f"files_not_in_use: {len(files_not_in_use)}, {files_not_in_use}")
    print(f"total_allocated_size: {mover.convert_bytes_to_human_readable(total_allocated_size)}")
    print(f"drive_free_space: {mover.convert_bytes_to_human_readable(drive_free_space)}")

    if total_allocated_size <= drive_free_space:
        print("Enough space to move all files.")
    else:
        print("Not enough space to move all files.")

    mover.move_files_if_space(src_directory, dst_directory)


if __name__ == "__main__":
    main()
