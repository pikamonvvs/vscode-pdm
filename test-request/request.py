class MyContextManager:
    def __init__(self, file_name):
        self.file_name = file_name

    def __enter__(self):
        print("Entering the context")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting the context")

    def print_filename(self):
        print(f"File name: {self.file_name}")


def open_file(file_name):
    return MyContextManager(file_name)


with open_file("asd.txt") as f:
    f.print_filename()
