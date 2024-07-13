import re
import subprocess


def run_ffmpeg(input_file, output_file):
    # ffmpeg 명령어 설정
    command = ["ffmpeg", "-i", input_file, "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-progress", "-", "-nostats", output_file]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    duration = None
    total_duration_re = re.compile(r"Duration: (\d+:\d+:\d+\.\d+)")
    time_re = re.compile(r"time=(\d+:\d+:\d+\.\d+)")

    while True:
        stderr_line = process.stderr.readline()
        if stderr_line == "" and process.poll() is not None:
            break

        if stderr_line:
            if duration is None:
                total_duration_match = total_duration_re.search(stderr_line)
                if total_duration_match:
                    duration = total_duration_match.group(1)
                    duration_seconds = time_to_seconds(duration)
                    print(f"Total Duration: {duration_seconds} seconds")

            time_match = time_re.search(stderr_line)
            if time_match:
                current_time = time_match.group(1)
                current_seconds = time_to_seconds(current_time)
                progress = (current_seconds / duration_seconds) * 100
                print(f"Progress: {progress:.2f}%")

    process.wait()


def time_to_seconds(time_str):
    h, m, s = map(float, time_str.split(":"))
    return h * 3600 + m * 60 + s


# 사용 예시
input_file = "input.ts"
output_file = "output.mp4"
run_ffmpeg(input_file, output_file)
