# config.py

# Define class constants for JSON keys
KEY_PLATFORM = "platform"
KEY_ID = "id"
KEY_NAME = "name"
KEY_INTERVAL = "interval"
KEY_FORMAT = "format"
KEY_OUTPUT = "output"
KEY_PROXY = "proxy"
KEY_COOKIES = "cookies"
KEY_HEADERS = "headers"
KEY_GROUPS = "groups"
KEY_USERS = "users"

DEFAULT_NAME = None
DEFAULT_INTERVAL = 10
DEFAULT_FORMAT = "ts"
DEFAULT_OUTPUT = "output"
DEFAULT_PROXY = None
DEFAULT_COOKIES = None
DEFAULT_HEADERS = {"User-Agent": "Chrome"}
DEFAULT_HEADERS_TIKTOK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
}
