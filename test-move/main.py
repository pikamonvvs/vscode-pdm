import ffmpeg
import streamlink

from ffmpeg_installer import FfmpegInstaller


def test_convert_flv_to_mp4(input_file, output_file):
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


def test_convert_mp4_to_avi(input_file, output_file):
    try:
        # FFmpeg 명령을 구성하고 실행
        (ffmpeg.input(input_file).output(output_file).run(overwrite_output=True, quiet=True))
        print(f"Conversion successful: {input_file} -> {output_file}")
    except ffmpeg.Error as e:
        print(f"Error: {e.stderr.decode('utf-8')}")
        raise e


def test_download_stream(url, output_file):
    streams = streamlink.streams(url)
    stream = streams["best"]
    with stream.open() as fd:
        process = (
            ffmpeg.input("pipe:0")
            .output(output_file, format="mp4", vcodec="copy", acodec="copy")
            .run_async(pipe_stdin=True)
        )

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
    my_ffmpeg = FfmpegInstaller()
    my_ffmpeg.run()

    # Convert MP4 to AVI
    input_file = "input.flv"
    output_file = "output.mp4"
    test_convert_flv_to_mp4(input_file, output_file)

    # Download stream
    # url = "https://www.example.com/"
    # output_file = "output.mp4"
    # test_download_stream(url, output_file)


if __name__ == "__main__":
    main()
