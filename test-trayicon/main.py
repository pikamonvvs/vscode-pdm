import os

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QSpacerItem,
    QSystemTrayIcon,
    QWidget,
)

ICON_BASEDIR = "res"
ICON_FILENAME = "icon.png"
ICON_PATH = os.path.join(ICON_BASEDIR, ICON_FILENAME)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(480, 80))  # Set sizes
        self.setWindowTitle("System Tray Application")  # Set a title

        # Create and set central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Create and set layout
        grid_layout = QGridLayout(self)
        central_widget.setLayout(grid_layout)

        # Add widgets to layout
        grid_layout.addWidget(QLabel("Application, which can minimize to Tray", self), 0, 0)
        self.check_box = QCheckBox("Minimize to Tray")
        grid_layout.addWidget(self.check_box, 1, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding), 2, 0)

        # Set up system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(ICON_PATH))

        # Create actions for tray icon menu
        show_action = QAction("Show", self)
        hide_action = QAction("Hide", self)
        quit_action = QAction("Exit", self)

        # Connect actions
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(QApplication.instance().quit)

        # Create tray icon menu and add actions
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)

        # Show tray icon
        self.tray_icon.show()

        # Connect tray icon double click event
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def closeEvent(self, event):
        if self.check_box.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("Tray Program", "Application was minimized to Tray", QSystemTrayIcon.MessageIcon.Information, 2000)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
