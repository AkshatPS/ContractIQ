import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QPointF
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView

from features.contract_diff import run_contract_diff


class DiffWorker(QThread):
    log_signal = Signal(str)
    result_signal = Signal(dict)

    def __init__(self, pdf1, pdf2):
        super().__init__()
        self.pdf1, self.pdf2 = pdf1, pdf2

    def run(self):
        try:
            self.log_signal.emit("Analyzing contracts...\n")
            results, error = run_contract_diff(self.pdf1, self.pdf2)
            if error:
                self.log_signal.emit(f"Error: {error}\n")
                return
            self.result_signal.emit(results)
        except Exception as e:
            import traceback
            self.log_signal.emit(traceback.format_exc())


class ContractDiffPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ContractIQ - Differences")
        self.showMaximized()

        self.pdf1, self.pdf2 = None, None
        self.path_removed, self.path_added = None, None
        self.pdf_doc = QPdfDocument(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        left = QWidget()
        self.left_layout = QVBoxLayout(left)

        self.pages_info = QLabel("Comparison results will appear here.")
        self.pages_info.setWordWrap(True)
        self.pages_info.setStyleSheet(
            "font-weight: bold; color: #380356; background: #f8f1ff; padding: 12px; border-radius: 8px;")

        self.switch_buttons = QWidget()
        btn_layout = QHBoxLayout(self.switch_buttons)
        self.btn_view_original = QPushButton("View Original (Red/Blue)")
        self.btn_view_modified = QPushButton("View Modified (Green/Blue)")

        btn_style = "padding: 12px; font-weight: bold; border-radius: 5px; color: white;"
        self.btn_view_original.setStyleSheet(btn_style + "background-color: #e74c3c;")
        self.btn_view_modified.setStyleSheet(btn_style + "background-color: #27ae60;")

        self.btn_view_original.clicked.connect(self.show_original)
        self.btn_view_modified.clicked.connect(self.show_modified)

        btn_layout.addWidget(self.btn_view_original)
        btn_layout.addWidget(self.btn_view_modified)
        self.switch_buttons.hide()

        self.pdf_viewer = QPdfView()
        self.pdf_viewer.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.pdf_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.page_counter = QLabel("Page: 0 / 0")
        self.page_counter.setStyleSheet("""
            color: #380356; 
            font-weight: bold; 
            background: #dcbdfb; 
            padding: 5px 15px; 
            border-radius: 15px;
        """)
        self.page_counter.setAlignment(Qt.AlignCenter)

        self.left_layout.addWidget(self.pages_info)
        self.left_layout.addWidget(self.switch_buttons)
        self.left_layout.addWidget(self.page_counter)
        self.left_layout.addWidget(self.pdf_viewer)

        right = QWidget()
        right.setFixedWidth(350)
        right.setStyleSheet("background-color: #380356; border-radius: 15px; padding: 15px;")
        r_layout = QVBoxLayout(right)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("color: white; text-align: left; background: none; border: none; font-weight: bold;")
        back_btn.clicked.connect(self.go_back)

        title = QLabel("Contract Difference")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")

        btn1 = QPushButton("Upload Original")
        btn2 = QPushButton("Upload Revised")
        run_btn = QPushButton("Compare Contracts")

        c_style = "background-color: #f8f1ff; color: #380356; font-weight: bold; padding: 12px; border-radius: 8px;"
        btn1.setStyleSheet(c_style);
        btn2.setStyleSheet(c_style)
        run_btn.setStyleSheet(
            "background-color: #dcbdfb; color: #380356; font-weight: bold; padding: 15px; border-radius: 8px;")

        btn1.clicked.connect(self.upload_pdf1);
        btn2.clicked.connect(self.upload_pdf2);
        run_btn.clicked.connect(self.run_diff)

        # Corrected log header
        log_header = QLabel("Process Logs:")
        log_header.setStyleSheet("color: white; font-weight: bold; margin-top: 10px;")

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet("background-color: #2a0242; color: #dcbdfb; border-radius: 8px;")

        r_layout.addWidget(back_btn);
        r_layout.addWidget(title)
        r_layout.addWidget(btn1);
        r_layout.addWidget(btn2);
        r_layout.addWidget(run_btn)
        r_layout.addSpacing(20)
        r_layout.addWidget(log_header)
        r_layout.addWidget(self.logs)

        layout.addWidget(left, 7);
        layout.addWidget(right, 3)

        self.pdf_viewer.pageNavigator().currentPageChanged.connect(self.update_page_label)

    def upload_pdf1(self):
        p, _ = QFileDialog.getOpenFileName(self, "Original", "", "PDF (*.pdf)")
        if p: self.pdf1 = p; self.logs.append(f"Loaded Original: {os.path.basename(p)}")

    def upload_pdf2(self):
        p, _ = QFileDialog.getOpenFileName(self, "Revised", "", "PDF (*.pdf)")
        if p: self.pdf2 = p; self.logs.append(f"Loaded Revised: {os.path.basename(p)}")

    def update_page_label(self):
        """Updates the 'Page X of Y' text based on current view."""
        nav = self.pdf_viewer.pageNavigator()
        current = nav.currentPage() + 1  # currentPage is 0-indexed
        total = self.pdf_doc.pageCount()
        if total > 0:
            self.page_counter.setText(f"Viewing Page: {current} / {total}")
        else:
            self.page_counter.setText("Page: 0 / 0")

    def run_diff(self):
        if self.pdf1 and self.pdf2:
            self.worker = DiffWorker(self.pdf1, self.pdf2)
            self.worker.log_signal.connect(self.logs.append)
            self.worker.result_signal.connect(self.display_results)
            self.worker.start()

    def display_results(self, res):
        self.path_removed, self.path_added = res["path_removed"], res["path_added"]
        p1 = ", ".join(map(str, sorted(list(res.get("pages1", [])))))
        p2 = ", ".join(map(str, sorted(list(res.get("pages2", [])))))
        self.pages_info.setText(
            f"Affected Original Pages: {p1 if p1 else 'None'}\nAffected Modified Pages: {p2 if p2 else 'None'}")
        self.switch_buttons.show()
        self.show_modified()

    def show_original(self):
        if self.path_removed:
            nav = self.pdf_viewer.pageNavigator()
            cur, zoom = nav.currentPage(), self.pdf_viewer.zoomFactor()
            self.pdf_doc.load(self.path_removed)
            self.pdf_viewer.setDocument(self.pdf_doc)
            # Use jump() to maintain position
            nav.jump(cur, QPointF(0, 0), zoom)
            self.update_page_label()
            self.btn_view_original.setStyleSheet(
                "padding: 12px; font-weight: bold; border-radius: 5px; color: white; background-color: #c0392b; border: 2px solid white;")
            self.btn_view_modified.setStyleSheet(
                "padding: 12px; font-weight: bold; border-radius: 5px; color: white; background-color: #27ae60; border: none;")

    def show_modified(self):
        if self.path_added:
            nav = self.pdf_viewer.pageNavigator()
            cur, zoom = nav.currentPage(), self.pdf_viewer.zoomFactor()
            self.pdf_doc.load(self.path_added)
            self.pdf_viewer.setDocument(self.pdf_doc)
            nav.jump(cur, QPointF(0, 0), zoom)
            self.update_page_label()
            self.btn_view_modified.setStyleSheet(
                "padding: 12px; font-weight: bold; border-radius: 5px; color: white; background-color: #1e8449; border: 2px solid white;")
            self.btn_view_original.setStyleSheet(
                "padding: 12px; font-weight: bold; border-radius: 5px; color: white; background-color: #e74c3c; border: none;")

    def go_back(self):
        from ui.home_page import HomePage
        self.home = HomePage();
        self.home.show();
        self.close()