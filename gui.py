from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel

def gui():
    app = QApplication([])

    window = QWidget()
    window.setWindowTitle("Enter Text to Close")
    window.setGeometry(100, 100, 400, 100)

    layout = QVBoxLayout()

    label = QLabel("Type something and hit Enter:")
    layout.addWidget(label)

    text_box = QLineEdit()
    layout.addWidget(text_box)

    def handle_enter():
        entered_text = text_box.text()
        print(f"You entered: {entered_text}")
        window.close()

    text_box.returnPressed.connect(handle_enter)

    window.setLayout(layout)
    window.show()
    app.exec()

if __name__ == "__main__":
    gui()
