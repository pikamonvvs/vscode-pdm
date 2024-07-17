import config
from json_processor import JSONProcessor

DEFAULT_JSON = "data.json"
DEFAULT_CMD = "argtest.exe"


class CommandBuilder:
    def __init__(self, complete_sets, command):
        self.user_options = complete_sets
        self.command = command
        self.arg_map = config.ARG_MAP

    # Convert headers dictionary to string and wrap in curly braces
    def jobj_to_str(self, headers):
        return "{" + ", ".join(f"{key}: {value}" for key, value in headers.items()) + "}"

    # Create argument list
    def create_args(self, user_config):
        args = []
        for key, arg in self.arg_map.items():
            value = user_config.get(key)
            if value is not None:
                args.append(arg)
                if key == config.KEY_INTERVAL:
                    args.append(str(value))  # Convert interval to string since it's an integer
                elif key == config.KEY_HEADERS:
                    args.append(self.jobj_to_str(value))
                else:
                    args.append(value)
        return args

    def build_commands(self):
        commands = []
        for user in self.user_options:
            platform = user.get(config.KEY_PLATFORM)
            user_id = user.get(config.KEY_ID)
            if not platform or not user_id:
                raise ValueError("Each user must have 'platform' and 'id' keys")
            # Add platform and id as positional arguments
            user_args = [platform, user_id] + self.create_args(user)
            if self.command:
                command = self.command
            else:
                command = user_args[0] + ".exe"
            full_command = [command] + user_args
            commands.append(full_command)
        return commands


def test():
    # Process JSON file to get complete sets
    processor = JSONProcessor(DEFAULT_JSON)
    user_options = processor.process()

    # Build commands using the complete sets
    builder = CommandBuilder(user_options, DEFAULT_CMD)
    commands = builder.build_commands()

    for cmd in commands:
        print(cmd)


if __name__ == "__main__":
    test()
