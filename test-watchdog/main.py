import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class MyHandler(FileSystemEventHandler):
    def __init__(self, file_extension):
        self.file_extension = file_extension

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_extension):
            print(f"New file created: {event.src_path}")

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith(self.file_extension):
            print(f"File moved to: {event.dest_path}")

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_extension):
            print(f"File modified: {event.src_path}")


if __name__ == "__main__":
    path = r"C:\Users\pcuser\Desktop\test-watchdog"  # 모니터링할 디렉토리 경로
    file_extension = ".txt"  # 감지할 파일 확장자

    event_handler = MyHandler(file_extension)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        print("observer start.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("observer stop.")
        observer.stop()
    observer.join()
