import os
import fitz
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QLineEdit, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from qa.qa_pipeline import QAPipeline


class InitWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        try:
            from pipelines.contract_pipeline import run_pipeline
            import json

            self.log_signal.emit("Running analysis pipeline (Classifying clauses)...")
            data = run_pipeline(self.pdf_path)

            filename = os.path.splitext(os.path.basename(self.pdf_path))[0]
            json_path = os.path.join("data/outputs/classified", f"{filename}.json")

            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.log_signal.emit("Extracting text for page-awareness...")
            doc = fitz.open(self.pdf_path)
            full_text_pages = [page.get_text("text") for page in doc]
            doc.close()

            self.log_signal.emit("Loading ML Models & Building Vector Index (Heavy Task)...")
            # Heavy ML task moved out of the main thread
            pipeline = QAPipeline(json_path, full_text_pages)

            self.finished_signal.emit(pipeline)
        except Exception as e:
            import traceback
            self.error_signal.emit(traceback.format_exc())


class QAWorker(QThread):
    log_signal = Signal(str)
    answer_signal = Signal(str)

    def __init__(self, qa_pipeline, question):
        super().__init__()
        self.qa_pipeline = qa_pipeline
        self.question = question

    def run(self):
        try:
            self.log_signal.emit("Searching vector space for relevant clauses...")
            answer = self.qa_pipeline.answer_question(self.question)
            self.answer_signal.emit(answer)
        except Exception as e:
            self.log_signal.emit(f"Error generating answer: {str(e)}")


class QAPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ContractIQ - Q&A System")
        self.showMaximized()
        self.qa_pipeline = None

        # Main Layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_container = QWidget()
        self.left_layout = QVBoxLayout(left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)

        self.status_banner = QLabel("Upload a contract to start asking questions.")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("""
            font-weight: bold; color: #380356; background-color: #f8f1ff; 
            padding: 15px; border: 1px solid #dcbdfb; border-radius: 8px;
        """)

        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setStyleSheet("background-color: #fcfcfc; border-radius: 8px;")

        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_area.setWidget(self.chat_widget)

        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question...")
        self.input_field.setEnabled(False)
        self.input_field.setStyleSheet("""
            QLineEdit { padding: 12px; border: 2px solid #dcbdfb; border-radius: 8px; color: black; background: white; }
            QLineEdit:focus { border: 2px solid #380356; }
        """)
        self.input_field.returnPressed.connect(self.send_question)

        self.send_btn = QPushButton("Send")
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet("""
            QPushButton { background-color: #380356; color: white; padding: 12px 25px; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #52067c; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.send_btn.clicked.connect(self.send_question)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)

        self.left_layout.addWidget(self.status_banner)
        self.left_layout.addWidget(self.chat_area)
        self.left_layout.addWidget(input_container)

        right_panel = QWidget()
        right_panel.setFixedWidth(350)
        right_panel.setStyleSheet("background-color: #380356; border-radius: 15px; padding: 15px;")
        right_layout = QVBoxLayout(right_panel)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("color: white; text-align: left; background: none; border: none; font-weight: bold;")
        back_btn.clicked.connect(self.go_back)

        self.upload_btn = QPushButton("Upload PDF")
        self.upload_btn.setStyleSheet("""
            QPushButton { background-color: #f8f1ff; color: #380356; padding: 12px; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #e9d5ff; }
        """)
        self.upload_btn.clicked.connect(self.upload_pdf)

        log_header = QLabel("Process Logs:")
        log_header.setStyleSheet("color: white; font-weight: bold; margin-top: 15px;")

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet("background-color: #2a0242; color: #dcbdfb; border-radius: 8px; font-family: Consolas;")

        right_layout.addWidget(back_btn)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.upload_btn)
        right_layout.addWidget(log_header)
        right_layout.addWidget(self.logs)

        main_layout.addWidget(left_container, 7)
        main_layout.addWidget(right_panel, 3)

    def upload_pdf(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if not file_path: return

        self.logs.clear()
        self.upload_btn.setEnabled(False)
        self.status_banner.setText("Loading AI Models... Windows might flicker briefly but UI will stay alive.")

        # Start Background Initialization
        self.init_thread = InitWorker(file_path)
        self.init_thread.log_signal.connect(self.update_logs)
        self.init_thread.finished_signal.connect(self.on_init_finished)
        self.init_thread.error_signal.connect(self.on_init_error)
        self.init_thread.start()

    def on_init_finished(self, pipeline):
        self.qa_pipeline = pipeline
        self.upload_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status_banner.setText("System Ready! Ask anything about the contract.")
        self.logs.append("\n[SUCCESS] Engine Ready.")

    def on_init_error(self, err_msg):
        self.logs.append(err_msg)
        self.status_banner.setText("Initialization Failed. Check logs.")
        self.upload_btn.setEnabled(True)

    def send_question(self):
        query = self.input_field.text().strip()
        if not query or not self.qa_pipeline: return

        self.input_field.clear()
        self.add_message(query, is_user=True)

        self.worker = QAWorker(self.qa_pipeline, query)
        self.worker.log_signal.connect(self.update_logs)
        self.worker.answer_signal.connect(self.show_answer)
        self.worker.start()

    def show_answer(self, answer):
        self.add_message(answer, is_user=False)

    def add_message(self, text, is_user):

        view_width = self.chat_area.viewport().width()

        # Fallback for initialization phase
        if view_width < 100: view_width = 800

        # Each bubble will be exactly 50% of the available width
        half_width = int(view_width * 0.5)

        # 2. Create the row container
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 10, 0, 10)  # Vertical spacing between messages
        layout.setSpacing(0)

        # 3. Create the bubble
        bubble = QLabel(text)
        bubble.setWordWrap(True)

        bubble.setFixedWidth(half_width)

        if is_user:
            layout.addStretch(1)  # This takes up exactly 50% of the empty space
            bubble.setStyleSheet("""
                background-color: #3498db;
                color: white;
                border-top-left-radius: 15px;
                border-bottom-left-radius: 15px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.4;
                border: none;
            """)
            layout.addWidget(bubble)
        else:
            bubble.setStyleSheet("""
                background-color: #f0f0f0;
                color: #2c3e50;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
                padding: 15px;
                font-size: 14px;
                border: 1px solid #e0e0e0;
                line-height: 1.4;
            """)
            layout.addWidget(bubble)
            layout.addStretch(1)  # This takes up exactly 50% of the empty space on the right

        # 4. Add to the main chat layout
        self.chat_layout.addWidget(container)

        # Force UI update and scroll
        container.show()
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )

    def update_logs(self, msg):
        self.logs.append(msg)

    def go_back(self):
        from ui.home_page import HomePage
        self.home = HomePage()
        self.home.show()
        self.close()