# import os

import streamlink

import ffmpeg
from classes.ffmpeg_installer import FfmpegInstaller


def convert_to_mp4(input_file, output_file):
    print(f"Converting {input_file} to MP4...")
    try:
        # Convert the file with copying codecs
        (ffmpeg.input(input_file).output(output_file, format="mp4", vcodec="copy", acodec="copy").run(overwrite_output=True, quiet=True))
        print(f"Converted {input_file} to {output_file}")
    except ffmpeg.Error as e:
        print(f"Error: {e.stderr.decode('utf-8')}")
        return False

    print(f"Conversion successful: {input_file} -> {output_file}")

    return True


def test_download_stream(url, output_file):
    streams = streamlink.streams(url)
    stream = streams["best"]
    with stream.open() as fd:
        process = ffmpeg.input("pipe:0").output(output_file, vcodec="copy", acodec="copy").run_async(pipe_stdin=True, overwrite_output=True)

        try:
            while True:
                data = fd.read(1024)
                if not data:
                    break
                process.stdin.write(data)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
        finally:
            process.stdin.close()
            process.wait()
            # if convert_to_mp4(output_file, output_file.replace(".ts", ".mp4")):
            #     os.remove(output_file)


def main():
    FfmpegInstaller().run()

    # Download stream
    # url = "https://www.twitch.tv/chodan_"
    url = "https://chzzk.naver.com/live/049a2d8aca5ec24e667ec70049780f4e"
    output_file = "output.ts"
    test_download_stream(url, output_file)


if __name__ == "__main__":
    main()
