from utils import logutil


class Recorder:
    def __init__(self):
        self.flag = "[asd][asd2]"

    def run(self):
        logutil.debug("This is an info log of recorder.")
        logutil.debug(self.flag, "This is an info log of recorder.")
        logutil.debug(self.flag, "This is an info log of recorder.", "asdasd")
