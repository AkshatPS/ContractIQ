import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView

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
            # Generate the brief report
            report_path = run_contract_brief(self.pdf_path)
            self.log_signal.emit("Processing complete. Generating preview...\n")
            self.finished_signal.emit(report_path)

        except Exception as e:
            import traceback
            self.log_signal.emit(traceback.format_exc())


class ContractBriefPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ContractIQ - Contract Brief")
        self.showMaximized()

        self.current_pdf_path = None
        self.pdf_doc = QPdfDocument(self)

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- LEFT PANEL: PDF Viewer Area (70% width) ---
        left_container = QWidget()
        self.pdf_layout = QVBoxLayout(left_container)
        self.pdf_layout.setContentsMargins(0, 0, 0, 0)

        # Status Banner
        self.status_banner = QLabel("Upload a contract to generate an AI-powered summary brief.")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("""
            font-weight: bold; 
            color: #380356; 
            background-color: #f8f1ff; 
            padding: 15px; 
            border: 1px solid #dcbdfb;
            border-radius: 8px;
        """)

        # PDF Viewer
        self.pdf_view = QPdfView()
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.pdf_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pdf_view.setStyleSheet("background-color: #f0f0f0; border-radius: 8px;")

        self.pdf_layout.addWidget(self.status_banner)
        self.pdf_layout.addWidget(self.pdf_view)

        main_layout.addWidget(left_container, 7)

        # --- RIGHT PANEL: Controls & Logs (30% width) ---
        right_panel = QWidget()
        right_panel.setFixedWidth(350)
        right_layout = QVBoxLayout(right_panel)
        right_panel.setStyleSheet("""
            background-color: #380356;
            border-radius: 15px;
            padding: 15px;
        """)

        # Back Button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("color: white; text-align: left; background: none; border: none; font-weight: bold;")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.go_back)

        # Title and Description
        title = QLabel("Contract Brief")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold; margin-top: 10px;")

        desc = QLabel("Automatically extract key terms, obligations, and summaries into a concise report.")
        desc.setStyleSheet("color: #dcbdfb; font-size: 13px;")
        desc.setWordWrap(True)

        # Action Button
        upload_btn = QPushButton("Upload PDF and Generate")
        upload_btn.setStyleSheet("""
            QPushButton { 
                background-color: #dcbdfb; 
                color: #380356; 
                padding: 15px; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 15px; 
                margin-top: 20px; 
            }
            QPushButton:hover { background-color: #e9d5ff; }
        """)
        upload_btn.setCursor(Qt.PointingHandCursor)
        upload_btn.clicked.connect(self.upload_pdf)

        # Log Section Header
        log_header = QLabel("Process Logs:")
        log_header.setStyleSheet("color: white; font-weight: bold; margin-top: 20px;")

        # Logs Window
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet("""
            background-color: #2a0242; 
            color: #dcbdfb; 
            border-radius: 8px; 
            font-family: 'Consolas', monospace; 
            font-size: 12px; 
            padding: 8px;
        """)
        self.logs.setPlaceholderText("Ready for processing...")

        # Add all elements to right layout
        right_layout.addWidget(back_btn)
        right_layout.addWidget(title)
        right_layout.addWidget(desc)
        right_layout.addWidget(upload_btn)
        right_layout.addSpacing(10)
        right_layout.addWidget(log_header)
        right_layout.addWidget(self.logs)

        main_layout.addWidget(right_panel, 3)
        self.setLayout(main_layout)

    def go_back(self):
        from ui.home_page import HomePage
        self.home = HomePage()
        self.home.show()
        self.close()

    def upload_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Contract PDF", "", "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        self.logs.clear()
        self.logs.append(f"Target file: {os.path.basename(file_path)}\n")
        self.status_banner.setText(f"Processing: {os.path.basename(file_path)}...")

        # Start background thread
        self.thread = WorkerThread(file_path)
        self.thread.log_signal.connect(self.update_logs)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def update_logs(self, message):
        self.logs.append(message)

    def on_finished(self, report_path):
        self.logs.append("\n[SUCCESS] Brief generated.")
        self.logs.append(f"Saved: {os.path.basename(report_path)}")

        self.status_banner.setText(f"Previewing Report: {os.path.basename(report_path)}")

        try:
            # Load and display the generated PDF brief
            self.pdf_doc.load(report_path)
            self.pdf_view.setDocument(self.pdf_doc)

        except Exception as e:
            self.logs.append(f"\n[ERROR] Preview failed: {str(e)}")