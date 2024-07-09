import sys

from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListView,
    QVBoxLayout,
    QWidget,
)


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age


class ListViewDemo(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.listView = QListView()
        self.model = QStandardItemModel()

        # Sample data
        people = [Person("Alice", 30), Person("Bob", 25), Person("Charlie", 35), Person("Diana", 28)]

        for person in people:
            item = QStandardItem(f"Name: {person.name}, Age: {person.age}")
            self.model.appendRow(item)

        self.listView.setModel(self.model)
        self.listView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # Disable editing

        layout.addWidget(self.listView)
        self.setLayout(layout)

        self.setWindowTitle("QListView Example")
        self.setGeometry(300, 300, 300, 200)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = ListViewDemo()
    demo.show()
    sys.exit(app.exec())
