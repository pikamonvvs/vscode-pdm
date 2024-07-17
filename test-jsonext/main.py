import subprocess

from command_builder import CommandBuilder
from json_processor import JSONProcessor

DEFAULT_JSON = "data.json"
DEFAULT_CMD = "argtest.exe"


def test():
    # Process JSON file to get complete sets
    processor = JSONProcessor(DEFAULT_JSON)
    user_options = processor.process()

    # Build commands using the complete sets
    builder = CommandBuilder(user_options, DEFAULT_CMD)
    commands = builder.build_commands()

    # Print the commands
    try:
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test()
