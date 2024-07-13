import signal
import subprocess
import sys

from command_builder import CommandBuilder

DEFAULT_CONFIG = "config.json"


def signal_handler(sig, frame):
    print("\nCtrl+C pressed. Exiting gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Get the command to run
    if len(sys.argv) < 2:
        print("Please provide a command to execute")
        sys.exit(-1)

    command = sys.argv[1]
    if ".exe" not in command:
        command = command + ".exe"

    # Get the config file path if provided
    if len(sys.argv) > 2:
        config = sys.argv[2]
    else:
        print(f"No config file path provided, using default config file: {DEFAULT_CONFIG}")
        config = DEFAULT_CONFIG

    builder = CommandBuilder(config, command)
    commands = builder.build_commands()

    # Print the commands
    print("==========================================")
    for cmd in commands:
        print(" ".join(cmd))
    print("==========================================")

    try:
        processes = []
        for cmd in commands:
            print("Command to run:", " ".join(cmd))
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Process started. (PID: {process.pid})")
            processes.append(process)
        for process in processes:
            process.wait()
            print(f"Process with PID {process.pid} exited with return code {process.returncode}")
    except KeyboardInterrupt:
        print("KeyboardInterrupt occurred")
        sys.exit(0)
