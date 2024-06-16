import ctypes
import os
import platform
import shutil

import ffmpeg


def get_drive_free_space(drive):
    """Return the free space of the drive in bytes."""
    if platform.system() == "Windows":
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(drive)
        return st.f_bavail * st.f_frsize


def get_file_allocated_size(file_path):
    """Return the allocated size of the file in bytes."""
    if platform.system() == "Windows":
        return os.path.getsize(file_path)
    else:
        st = os.stat(file_path)
        block_size = os.statvfs(file_path).f_frsize
        allocated_size = ((st.st_size + block_size - 1) // block_size) * block_size
        return allocated_size


def is_file_in_use(file_path):
    """Check if a file is currently in use."""
    try:
        os.rename(file_path, file_path)
        return False
    except OSError:
        return True


def get_files_not_used_in_directory(directory):
    """Return a list of files in the given directory (depth 1 only) that are not in use."""
    files = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path) and item_path.endswith((".flv", ".mp4", ".ts")) and not is_file_in_use(item_path):
            files.append(item_path)
    return files


def convert_bytes_to_human_readable(size, decimal_places=2):
    """Convert a size in bytes to a human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]:
        if size < 1024.0:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0


def convert_to_mp4(input_file, output_file):
    file_allocated_size = get_file_allocated_size(input_file)
    dst_drive = os.path.splitdrive(output_file)[0] + os.path.sep
    free_drive_space = get_drive_free_space(dst_drive)

    if file_allocated_size > free_drive_space:
        print(f"Not enough {dst_drive} space to convert {input_file} to MP4.")
        return False

    print(f"Converting {input_file} to MP4...")
    try:
        (
            ffmpeg.input(input_file)
            .output(output_file, format="mp4", vcodec="copy", acodec="copy")
            .run(overwrite_output=True, quiet=True)
        )
        print(f"Converted {input_file} to {output_file}")
    except ffmpeg.Error as e:
        print(f"Error: {e.stderr.decode('utf-8')}")
        raise e

    return True


def move_files_if_space(src_directory, dst_directory):
    """Move files from src_directory to dst_directory if there is enough free space on the destination drive."""
    files_to_move = get_files_not_used_in_directory(src_directory)
    total_allocated_size = sum(get_file_allocated_size(f) for f in files_to_move)

    dst_drive = os.path.splitdrive(dst_directory)[0] + os.path.sep
    free_space = get_drive_free_space(dst_drive)

    print(f"Total allocated size of files to move: {convert_bytes_to_human_readable(total_allocated_size)}")
    print(f"Free space on destination drive: {convert_bytes_to_human_readable(free_space)}")

    if total_allocated_size <= free_space:
        for file_path in files_to_move:
            dst_path = os.path.join(dst_directory, os.path.relpath(file_path, src_directory))

            print(f"Checking if {file_path} needs to be converted to MP4...")

            if file_path.endswith(".flv"):
                file_path_mp4 = file_path.replace(".flv", ".mp4")
                if not convert_to_mp4(file_path, file_path_mp4):
                    continue
                os.remove(file_path)
                file_path = file_path_mp4
                dst_path = dst_path.replace(".flv", ".mp4")
            elif file_path.endswith(".mp4"):
                file_path_temp = file_path + ".tmp"
                if not convert_to_mp4(file_path, file_path_temp):
                    continue
                shutil.move(file_path_temp, file_path)

            print(f"Moving file from {file_path} to {dst_path}")
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(file_path, dst_path)
            print(f"File moved from {file_path} to {dst_path}")
    else:
        print(f"Not enough {dst_drive} space on the destination drive to move all files.")


if __name__ == "__main__":
    src_directory = input("Enter the source directory: ").strip('"')
    if not src_directory:
        src_directory = r"Z:\\"
    dst_directory = input("Enter the destination directory: ").strip('"')
    if not dst_directory:
        dst_directory = r"D:\Works"

    files_to_move = get_files_not_used_in_directory(src_directory)
    files_to_move_count = len(files_to_move)
    total_allocated_size = sum(get_file_allocated_size(f) for f in files_to_move)
    free_space = get_drive_free_space(os.path.splitdrive(dst_directory)[0] + os.path.sep)

    print(f"files_count: {len(files_to_move)}")
    print(f"files_to_move: {files_to_move}")
    print(f"total_allocated_size: {convert_bytes_to_human_readable(total_allocated_size)}")
    print(f"free_space: {convert_bytes_to_human_readable(free_space)}")

    if total_allocated_size <= free_space:
        print("Enough space to move all files.")
    else:
        print("Not enough space to move all files.")

    move_files_if_space(src_directory, dst_directory)
