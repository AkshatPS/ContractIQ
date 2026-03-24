import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout
)
from PySide6.QtCore import Qt, QThread, Signal

from features.contract_brief import run_contract_brief

class WorkerThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(str)

    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        try:
            self.log_signal.emit("Starting contract processing...\n")

            report_path = run_contract_brief(self.pdf_path)

            self.log_signal.emit("Processing complete.\n")

            self.finished_signal.emit(report_path)

        except Exception as e:
            import traceback
            self.log_signal.emit(traceback.format_exc())


class ContractBriefPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Contract Brief")
        self.showMaximized()

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)


        self.pdf_container = QWidget()
        self.pdf_layout = QVBoxLayout()
        self.pdf_container.setLayout(self.pdf_layout)

        main_layout.addWidget(self.pdf_container, 7)


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
        title = QLabel("Contract Brief")
        title.setObjectName("title")

        # Description
        desc = QLabel("Generate a concise AI-powered summary of your contract.")
        desc.setWordWrap(True)

        # Upload Button
        upload_btn = QPushButton("Upload PDF")
        upload_btn.setFixedHeight(40)
        upload_btn.clicked.connect(self.upload_pdf)

        # Logs
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setPlaceholderText("Logs will appear here...")

        # Add widgets
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

        self.logs.clear()
        self.logs.append(f"Selected file:\n{file_path}\n")

        # Start worker thread
        self.thread = WorkerThread(file_path)
        self.thread.log_signal.connect(self.update_logs)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def update_logs(self, message):
        self.logs.append(message)

    def on_finished(self, pdf_path):

        self.logs.append("\n🎉 Brief created successfully!")
        self.logs.append("Saved in data/outputs/reports folder.\n")

        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView

            for i in reversed(range(self.pdf_layout.count())):
                widget = self.pdf_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

            # Load PDF
            self.pdf_doc = QPdfDocument()
            self.pdf_doc.load(pdf_path)

            self.pdf_view = QPdfView()
            self.pdf_view.setDocument(self.pdf_doc)

            # MULTI-PAGE + SCROLL FIX
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

            self.pdf_layout.addWidget(self.pdf_view)

        except Exception as e:
            self.logs.append(f"\nPDF preview failed: {str(e)}")