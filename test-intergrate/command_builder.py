import json
import os
import subprocess


class CommandBuilder:
    def __init__(self, json_file_path, command):
        self.json_file_path = json_file_path
        self.command = command
        self.arg_map = {"proxy": "-p", "interval": "-i", "format": "-f", "output": "-o", "headers": "-H", "cookies": "-c", "name": "-n"}

    # Function to read the JSON file
    def read_json_file(self):
        with open(self.json_file_path, "r") as file:
            return json.load(file)

    # Convert headers dictionary to string and wrap in curly braces
    def headers_to_string(self, headers):
        return "{" + ", ".join(f"{key}: {value}" for key, value in headers.items()) + "}"

    # Create argument list
    def create_args(self, global_config, user_config):
        args = []
        for key, arg in self.arg_map.items():
            value = user_config.get(key, global_config.get(key))
            if value is not None:
                args.append(arg)
                if key == "interval":
                    args.append(str(value))  # Convert interval to string since it's an integer
                elif key == "headers":
                    args.append(self.headers_to_string(value))
                else:
                    args.append(value)
        return args

    def build_commands(self):
        config = self.read_json_file()

        global_config = {key: config[key] for key in config if key != "users"}
        users = config.get("users", [])

        commands = []
        for user in users:
            platform = user.get("platform")
            user_id = user.get("id")

            if not platform or not user_id:
                raise ValueError("Each user must have 'platform' and 'id' keys")

            # Add platform and id as positional arguments
            user_args = [platform, user_id] + self.create_args(global_config, user)

            # full_command = [self.command] + user_args
            command = os.path.join(".", user_args[0] + ".exe")

            full_command = [command] + user_args
            commands.append(full_command)

        return commands


def test():
    builder = CommandBuilder("config.json", "Test.exe")
    commands = builder.build_commands()

    # Print the commands
    for cmd in commands:
        print("Command to run:", " ".join(cmd))
        subprocess.run(cmd)


if __name__ == "__main__":
    test()
