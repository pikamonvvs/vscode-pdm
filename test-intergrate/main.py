import os
import subprocess
import sys

import psutil
from PyQt6.QtCore import QSettings, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from command_builder import CommandBuilder

ICON_BASEDIR = "res"
ICON_FILENAME = "icon.png"
ICON_PATH = os.path.join(ICON_BASEDIR, ICON_FILENAME)

DEFAULT_CONFIG = "config.json"


class ExternalProgramRunner(QWidget):
    def __init__(self, commands):
        super().__init__()

        self.commands = commands
        self.processes = [None] * len(commands)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        layout.addWidget(self.logs)

        self.start_all_btn = QPushButton("Start All")
        self.start_all_btn.clicked.connect(self.start_all)
        layout.addWidget(self.start_all_btn)

        self.stop_all_btn = QPushButton("Stop All")
        self.stop_all_btn.clicked.connect(self.stop_all)
        layout.addWidget(self.stop_all_btn)

        self.restart_all_btn = QPushButton("Restart All")
        self.restart_all_btn.clicked.connect(self.restart_all)
        layout.addWidget(self.restart_all_btn)

        self.program_buttons = []
        self.status_labels = []

        grid_layout = QGridLayout()

        for i, command in enumerate(self.commands):
            label = QLabel(f"Program {i + 1}: {command}")
            grid_layout.addWidget(label, i, 0, 1, 3)

            start_btn = QPushButton("Start")
            start_btn.clicked.connect(lambda _, idx=i: self.start_program(idx))
            grid_layout.addWidget(start_btn, i, 3)

            stop_btn = QPushButton("Stop")
            stop_btn.clicked.connect(lambda _, idx=i: self.stop_program(idx))
            grid_layout.addWidget(stop_btn, i, 4)

            restart_btn = QPushButton("Restart")
            restart_btn.clicked.connect(lambda _, idx=i: self.restart_program(idx))
            grid_layout.addWidget(restart_btn, i, 5)

            status_label = QLabel("Not Running")
            self.status_labels.append(status_label)
            grid_layout.addWidget(status_label, i, 6)

            self.program_buttons.append((start_btn, stop_btn, restart_btn))

        layout.addLayout(grid_layout)

        self.setLayout(layout)
        self.setWindowTitle("External Program Runner")
        self.resize(800, 600)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)

    def log(self, message):
        self.logs.append(message)

    def start_program(self, index):
        if self.processes[index] is None or self.processes[index].poll() is not None:
            self.processes[index] = subprocess.Popen(self.commands[index], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            self.log(f"Started Program {index + 1}: {self.commands[index]}")

    def stop_program(self, index):
        if self.processes[index] is not None and self.processes[index].poll() is None:
            parent = psutil.Process(self.processes[index].pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            gone, still_alive = psutil.wait_procs(parent.children(recursive=True), timeout=3)
            for p in still_alive:
                p.kill()
            self.processes[index] = None
            self.log(f"Stopped Program {index + 1}: {self.commands[index]}")

    def stop_all(self):
        for i in range(len(self.commands)):
            self.stop_program(i)
        self.log("Stopped all programs")

    def restart_program(self, index):
        self.stop_program(index)
        self.start_program(index)
        self.log(f"Restarted Program {index + 1}: {self.commands[index]}")

    def start_all(self):
        for i in range(len(self.commands)):
            self.start_program(i)
        self.log("Started all programs")

    def restart_all(self):
        for i in range(len(self.commands)):
            self.restart_program(i)
        self.log("Restarted all programs")

    def update_status(self):
        for i, process in enumerate(self.processes):
            if process is None or process.poll() is not None:
                self.status_labels[i].setText("Not Running")
            else:
                self.status_labels[i].setText("Running")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(1280, 960))
        self.setWindowTitle("System Tray Application with External Program Runner")

        config = DEFAULT_CONFIG
        command = "Test.exe"  # FIXME: dummy command
        builder = CommandBuilder(config, command)
        commands = builder.build_commands()
        self.runner = ExternalProgramRunner(commands)
        self.setCentralWidget(self.runner)

        self.initUI()

    def initUI(self):
        self.check_box = QCheckBox("Minimize to Tray")
        self.runner.layout().addWidget(self.check_box)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(ICON_PATH))

        show_action = QAction("Show", self)
        hide_action = QAction("Hide", self)
        quit_action = QAction("Exit", self)

        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(self.quit_application)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        self.load_settings()
        self.check_box.stateChanged.connect(self.save_settings)

    def closeEvent(self, event):
        if self.check_box.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("Tray Program", "Application was minimized to Tray", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self.runner.stop_all()  # Stop all programs when the application is closed
            self.save_settings()
            event.accept()

    def quit_application(self):
        self.runner.stop_all()  # Stop all programs when quitting the application
        QApplication.instance().quit()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()

    def load_settings(self):
        settings = QSettings("MyCompany", "MyApp")
        minimize_to_tray = settings.value("minimize_to_tray", False, type=bool)
        self.check_box.setChecked(minimize_to_tray)

    def save_settings(self):
        settings = QSettings("MyCompany", "MyApp")
        settings.setValue("minimize_to_tray", self.check_box.isChecked())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
