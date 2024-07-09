import sys
import time


def print_spinner_line(line_num, spinner_char):
    # Move the cursor to the specified line
    sys.stdout.write(f"\033[{line_num}F")  # Move cursor up by line_num lines
    sys.stdout.write(f"\r{spinner_char}")  # Carriage return and print spinner character
    sys.stdout.flush()


def multi_spinner(num_lines):
    spinner_chars = ["-", "\\", "|", "/"]
    idx = 0

    try:
        while True:
            for line in range(num_lines):
                print_spinner_line(line + 1, spinner_chars[(idx + line) % len(spinner_chars)])
            idx += 1
            time.sleep(0.1)  # Adjust the speed of the spinner
    except KeyboardInterrupt:
        print("\nSpinners stopped.")


if __name__ == "__main__":
    num_lines = 5  # Number of spinner lines
    # Print initial empty lines
    for _ in range(num_lines):
        print()
    multi_spinner(num_lines)
