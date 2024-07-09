import msvcrt  # Only available on Windows

import keyboard


class KeyboardListener:
    def __init__(self):
        self.running = True

    def on_key_event(self, event):
        print(f"Key '{event.name}' was pressed.")

    def on_enter_key(self, event):
        print("Enter key was pressed. Performing specific action.")

    def start_listening(self):
        print("Detecting keyboard input. Press 'esc' key to exit.")
        # Call callback function when a specific key is pressed.
        keyboard.on_press(self.on_key_event)
        keyboard.on_press_key("enter", self.on_enter_key)
        # Exit the program when 'esc' key is pressed.
        keyboard.wait("esc")
        print("Program has exited.")
        self.clear_input_buffer()

    def clear_input_buffer(self):
        while msvcrt.kbhit():
            msvcrt.getch()
