import json

import config


class JSONProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.complete_sets = []

    def load_json(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.data = json.load(file)
        except json.JSONDecodeError:
            raise ValueError("The JSON file is not properly formatted.")
        except FileNotFoundError:
            raise ValueError("The JSON file was not found.")
        except Exception as e:
            raise ValueError(f"An unexpected error occurred while reading the file: {e}")

    def validate_keys(self, data, required_keys, context=""):
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key} in {context}")

    def validate_data(self):
        # Check for required global keys
        self.validate_keys(self.data, config.REQUIRED_GLOBAL_KEYS, "global data")

        # Check if groups is a list
        if not isinstance(self.data[config.KEY_GROUPS], list):
            raise ValueError("The 'groups' key must be a list")

        for group in self.data[config.KEY_GROUPS]:
            # Check for required group keys
            self.validate_keys(group, config.REQUIRED_GROUP_KEYS, f"group {group}")

            # Check if users is a list
            if not isinstance(group[config.KEY_USERS], list):
                raise ValueError(f"The 'users' key must be a list in group {group}")

            for user in group[config.KEY_USERS]:
                # Check for required user keys
                self.validate_keys(user, config.REQUIRED_USER_KEYS, f"user {user}")

    def merge_options(self, primary, secondary, keys):
        return {key: primary.get(key, secondary.get(key)) for key in keys}

    def generate_complete_sets(self):
        global_options = {key: self.data.get(key) for key in config.GLOBAL_KEYS}

        for group in self.data[config.KEY_GROUPS]:
            group_options = self.merge_options(group, global_options, config.GLOBAL_KEYS)

            for user in group[config.KEY_USERS]:
                user_options = self.merge_options(user, group_options, config.USER_KEYS)
                user_options[config.KEY_ID] = user[config.KEY_ID]  # Ensure ID is always taken from user
                self.complete_sets.append(user_options)

    def process(self):
        self.load_json()
        self.validate_data()
        self.generate_complete_sets()
        return self.complete_sets


def test():
    # JSON file path
    file_path = "data.json"

    # Create and process JSONProcessor instance
    processor = JSONProcessor(file_path)
    try:
        complete_sets = processor.process()
        # Print results
        print(json.dumps(complete_sets, ensure_ascii=False, indent=4))
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    test()
