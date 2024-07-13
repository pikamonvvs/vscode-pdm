import subprocess
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Process Monitor")

        self.processes = []
        self.process_labels = []
        self.restart_buttons = []

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.start_button = QPushButton("Start Processes")
        self.start_button.clicked.connect(self.start_processes)
        self.layout.addWidget(self.start_button)

        self.status_layout = QGridLayout()
        self.layout.addLayout(self.status_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)

    def start_processes(self):
        # Windows용 명령어
        commands = ["ping -n 4 google.com", "ping -n 4 yahoo.com"]
        for i, cmd in enumerate(commands):
            self.start_process(cmd, i)

    def start_process(self, cmd, index):
        log_file = open(f"process_{index}.txt", "w", encoding="utf-8")
        process = subprocess.Popen(cmd, shell=True, stdout=log_file, stderr=log_file)
        self.processes.append(process)

        label = QLabel(f"Process {index + 1}: Running")
        self.status_layout.addWidget(label, index, 0)
        self.process_labels.append(label)

        button = QPushButton("Restart")
        button.clicked.connect(lambda _, idx=index: self.restart_process(idx))
        self.status_layout.addWidget(button, index, 1)
        self.restart_buttons.append(button)

    def restart_process(self, index):
        # 기존 프로세스를 종료합니다.
        if self.processes[index].poll() is None:
            self.processes[index].terminate()
            self.processes[index].wait()

        # 프로세스를 재시작합니다.
        cmd = self.processes[index].args
        log_file = open(f"process_{index}.txt", "w", encoding="utf-8")
        self.processes[index] = subprocess.Popen(cmd, shell=True, stdout=log_file, stderr=log_file)
        self.process_labels[index].setText(f"Process {index + 1}: Running")

    def update_status(self):
        for i, process in enumerate(self.processes):
            if process.poll() is None:
                self.process_labels[i].setText(f"Process {i + 1}: Running")
            else:
                self.process_labels[i].setText(f"Process {i + 1}: Finished")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = App()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("Keyboard Interrupt occurred.")
