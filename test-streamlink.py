import streamlink

import ffmpeg
from classes.ffmpeg_installer import FfmpegInstaller


def test_download_stream(self, url, output_file):
    streams = streamlink.streams(url)
    stream = streams["best"]
    with stream.open() as fd:
        process = ffmpeg.input("pipe:0").output(output_file, format="mp4", vcodec="copy", acodec="copy").run_async(pipe_stdin=True)

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


def main():
    FfmpegInstaller().run()

    # Download stream
    url = "https://www.example.com/"
    output_file = "output.mp4"
    test_download_stream(url, output_file)


if __name__ == "__main__":
    main()
