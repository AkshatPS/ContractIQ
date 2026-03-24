import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QLineEdit, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from features.qa_system import run_qa_system

class QAWorker(QThread):
    log_signal = Signal(str)
    answer_signal = Signal(str)

    def __init__(self, pdf_path, question):
        super().__init__()
        self.pdf_path = pdf_path
        self.question = question

    def run(self):
        try:
            self.log_signal.emit("🤖 Processing question...\n")

            answer = run_qa_system(self.pdf_path, self.question)

            self.answer_signal.emit(answer)

        except Exception as e:
            import traceback
            self.log_signal.emit(traceback.format_exc())


class QAPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Q&A System")
        self.showMaximized()

        self.pdf_path = None

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_container = QWidget()
        left_layout = QVBoxLayout()
        left_container.setLayout(left_layout)

        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)

        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(15)
        self.chat_widget.setLayout(self.chat_layout)

        self.chat_area.setWidget(self.chat_widget)

        input_layout = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question about the contract...")

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_question)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)

        left_layout.addWidget(self.chat_area)
        left_layout.addLayout(input_layout)

        main_layout.addWidget(left_container, 7)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        right_panel.setStyleSheet("""
        background-color: #380356;
        border-radius: 15px;
        padding: 10px;
        """)

        # Back Button
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.go_back)

        # Title
        title = QLabel("Q&A System")
        title.setObjectName("title")

        # Description
        desc = QLabel("Ask questions and get intelligent answers from your contract.")
        desc.setWordWrap(True)

        # Upload Button
        upload_btn = QPushButton("Upload PDF")
        upload_btn.clicked.connect(self.upload_pdf)

        # Logs
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setPlaceholderText("Logs will appear here...")

        right_layout.addWidget(back_btn)
        right_layout.addWidget(title)
        right_layout.addWidget(desc)
        right_layout.addSpacing(10)
        right_layout.addWidget(upload_btn)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.logs)

        main_layout.addWidget(right_panel, 3)

        self.setLayout(main_layout)

    def go_back(self):
        from ui.home_page import HomePage
        self.home = HomePage()
        self.home.show()
        self.close()

    def upload_pdf(self):
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        self.pdf_path = file_path
        self.logs.append(f"Loaded file:\n{file_path}\n")
        self.logs.append("Ready for Q&A\n")

    def send_question(self):
        question = self.input_field.text().strip()

        if not question:
            return

        if not self.pdf_path:
            self.logs.append("Please upload a PDF first.\n")
            return

        self.input_field.clear()

        # Add question to chat
        self.add_message(question, is_user=True)

        # Start worker
        self.thread = QAWorker(self.pdf_path, question)
        self.thread.log_signal.connect(self.update_logs)
        self.thread.answer_signal.connect(self.show_answer)
        self.thread.start()


    def show_answer(self, answer):
        self.add_message(answer, is_user=False)


    def add_message(self, text, is_user):

        label_prefix = "Q: " if is_user else "A: "

        msg = QLabel(label_prefix + text)
        msg.setWordWrap(True)

        msg.setStyleSheet("""
            font-size: 15px;
            padding: 8px;
            color: white;
        """)

        msg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(msg)

        container.setLayout(layout)

        self.chat_layout.addWidget(container)

        # Auto scroll
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )

    def update_logs(self, message):
        self.logs.append(message)