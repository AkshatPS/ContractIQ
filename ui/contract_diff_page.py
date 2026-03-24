import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal

from features.contract_diff import run_contract_diff


class DiffWorker(QThread):
    log_signal = Signal(str)
    result_signal = Signal(dict)

    def __init__(self, pdf1, pdf2):
        super().__init__()
        self.pdf1 = pdf1
        self.pdf2 = pdf2

    def run(self):
        try:
            self.log_signal.emit("Running contract comparison...\n")

            results, _ = run_contract_diff(self.pdf1, self.pdf2)

            self.log_signal.emit("Comparison complete.\n")

            self.result_signal.emit(results)

        except Exception as e:
            import traceback
            self.log_signal.emit(traceback.format_exc())

class ContractDiffPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Contract Difference")
        self.showMaximized()

        self.pdf1 = None
        self.pdf2 = None

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_container = QWidget()
        left_layout = QVBoxLayout()
        left_container.setLayout(left_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.result_widget = QWidget()
        self.result_layout = QVBoxLayout()
        self.result_layout.setAlignment(Qt.AlignTop)

        self.result_widget.setLayout(self.result_layout)
        self.scroll_area.setWidget(self.result_widget)

        left_layout.addWidget(self.scroll_area)

        main_layout.addWidget(left_container, 7)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        right_panel.setStyleSheet("""
        background-color: #380356;
        border-radius: 15px;
        padding: 10px;
        """)

        # Back
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.go_back)

        # Title
        title = QLabel("Contract Difference")
        title.setObjectName("title")

        # Description
        desc = QLabel("Compare two contracts and identify added, removed, and modified clauses.")
        desc.setWordWrap(True)

        # Upload buttons
        btn1 = QPushButton("Upload Contract A")
        btn2 = QPushButton("Upload Contract B")

        btn1.clicked.connect(self.upload_pdf1)
        btn2.clicked.connect(self.upload_pdf2)

        # Run button
        run_btn = QPushButton("Compare Contracts")
        run_btn.clicked.connect(self.run_diff)

        # Logs
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)

        # Add widgets
        right_layout.addWidget(back_btn)
        right_layout.addWidget(title)
        right_layout.addWidget(desc)
        right_layout.addSpacing(10)
        right_layout.addWidget(btn1)
        right_layout.addWidget(btn2)
        right_layout.addWidget(run_btn)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.logs)

        main_layout.addWidget(right_panel, 3)

        self.setLayout(main_layout)

    def upload_pdf1(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Contract A", "", "PDF Files (*.pdf)")
        if path:
            self.pdf1 = path
            self.logs.append(f"Contract A loaded\n{path}\n")

    def upload_pdf2(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Contract B", "", "PDF Files (*.pdf)")
        if path:
            self.pdf2 = path
            self.logs.append(f"Contract B loaded\n{path}\n")


    def run_diff(self):
        if not self.pdf1 or not self.pdf2:
            self.logs.append("Please upload both contracts.\n")
            return

        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.result_layout.setAlignment(Qt.AlignTop)

        self.thread = DiffWorker(self.pdf1, self.pdf2)
        self.thread.log_signal.connect(self.update_logs)
        self.thread.result_signal.connect(self.display_results)
        self.thread.start()

    def display_results(self, results):

        # Safety extraction
        added = results.get("added", [])
        removed = results.get("removed", [])
        modified = results.get("modified", [])

        # Clear old UI
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        metrics = QLabel(
            f"Added: {len(added)}   |   Removed: {len(removed)}   |   Modified: {len(modified)}"
        )
        metrics.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.result_layout.addWidget(metrics)

        self.add_section("Added Clauses", added)

        self.add_section("Removed Clauses", removed)

        if modified:
            label = QLabel("Modified Clauses")
            label.setStyleSheet("font-size: 16px; font-weight: bold;")
            self.result_layout.addWidget(label)

            for m in modified:
                old = m.get("old", "")
                new = m.get("new", "")

                text = f"OLD: {old}\nNEW: {new}"
                self.add_item(text)

    def add_section(self, title, items):
        if not items:
            return

        label = QLabel(title)
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.result_layout.addWidget(label)

        for item in items:
            self.add_item(item)

    def add_item(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("padding: 6px;")
        self.result_layout.addWidget(lbl)

    def update_logs(self, msg):
        self.logs.append(msg)

    def go_back(self):
        from ui.home_page import HomePage
        self.home = HomePage()
        self.home.show()
        self.close()