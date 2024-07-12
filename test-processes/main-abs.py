import subprocess
import sys
from abc import ABC, abstractmethod

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GUIInterface(ABC):
    @abstractmethod
    def set_window_title(self, title: str):
        pass

    @abstractmethod
    def add_start_button(self, callback):
        pass

    @abstractmethod
    def add_status_label(self, text: str):
        pass

    @abstractmethod
    def add_restart_button(self, index: int, callback):
        pass

    @abstractmethod
    def update_status_label(self, index: int, text: str):
        pass

    @abstractmethod
    def start_timer(self, interval: int, callback):
        pass

    @abstractmethod
    def show(self):
        pass

    @abstractmethod
    def exec(self):
        pass


####


class PyQt6GUI(GUIInterface):
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = QWidget()
        self.window.setWindowTitle("Process Monitor")
        self.layout = QVBoxLayout()
        self.window.setLayout(self.layout)
        self.status_layout = QGridLayout()
        self.layout.addLayout(self.status_layout)
        self.process_labels = []

    def set_window_title(self, title: str):
        self.window.setWindowTitle(title)

    def add_start_button(self, callback):
        start_button = QPushButton("Start Processes")
        start_button.clicked.connect(callback)
        self.layout.addWidget(start_button)

    def add_status_label(self, text: str):
        label = QLabel(text)
        self.status_layout.addWidget(label, len(self.process_labels), 0)
        self.process_labels.append(label)

    def add_restart_button(self, index: int, callback):
        button = QPushButton("Restart")
        button.clicked.connect(lambda: callback(index))
        self.status_layout.addWidget(button, index, 1)

    def update_status_label(self, index: int, text: str):
        self.process_labels[index].setText(text)

    def start_timer(self, interval: int, callback):
        self.timer = QTimer()
        self.timer.timeout.connect(callback)
        self.timer.start(interval)

    def show(self):
        self.window.show()

    def exec(self):
        sys.exit(self.app.exec())


####


class ProcessMonitor:
    def __init__(self, gui: GUIInterface):
        self.gui = gui
        self.processes = []
        self.gui.set_window_title("Process Monitor")
        self.gui.add_start_button(self.start_processes)
        self.gui.start_timer(1000, self.update_status)

    def start_processes(self):
        commands = ["ping -n 4 google.com", "ping -n 4 yahoo.com"]
        for i, cmd in enumerate(commands):
            self.start_process(cmd, i)

    def start_process(self, cmd, index):
        log_file = open(f"process_{index}.txt", "w", encoding="utf-8")
        process = subprocess.Popen(cmd, shell=True, stdout=log_file, stderr=log_file)
        self.processes.append(process)
        self.gui.add_status_label(f"Process {index + 1}: Running")
        self.gui.add_restart_button(index, self.restart_process)

    def restart_process(self, index):
        if self.processes[index].poll() is None:
            self.processes[index].terminate()
            self.processes[index].wait()
        cmd = self.processes[index].args
        log_file = open(f"process_{index}.txt", "w", encoding="utf-8")
        self.processes[index] = subprocess.Popen(cmd, shell=True, stdout=log_file, stderr=log_file)
        self.gui.update_status_label(index, f"Process {index + 1}: Running")

    def update_status(self):
        for i, process in enumerate(self.processes):
            if process.poll() is None:
                self.gui.update_status_label(i, f"Process {i + 1}: Running")
            else:
                self.gui.update_status_label(i, f"Process {i + 1}: Finished")


####

if __name__ == "__main__":
    try:
        gui = PyQt6GUI()
        monitor = ProcessMonitor(gui)
        gui.show()
        gui.exec()
    except KeyboardInterrupt:
        print("Keyboard Interrupt occurred.")
