import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor


class HomePage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ContractIQ - Home")
        self.showMaximized()

        # Set page background to your dark preference
        self.setStyleSheet("background-color: #1e1e1e;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(80, 40, 80, 60)
        main_layout.setAlignment(Qt.AlignCenter)

        # --- Header Section ---
        header_container = QVBoxLayout()

        title = QLabel("ContractIQ Dashboard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 42px; 
            font-weight: bold; 
            color: #dcbdfb; 
            margin-bottom: 5px;
            background: transparent;
        """)

        subtitle = QLabel("Powerful AI-driven legal tools for modern contract analysis.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 18px; 
            color: #aaaaaa; 
            margin-bottom: 40px;
            background: transparent;
        """)

        header_container.addWidget(title)
        header_container.addWidget(subtitle)
        main_layout.addLayout(header_container)

        # --- Feature Cards Layout ---
        card_layout = QHBoxLayout()
        card_layout.setSpacing(40)

        # Card 1: Contract Brief
        # Corrected: Passing exactly 3 arguments to match the updated definition
        card1 = self.create_feature_card(
            "Contract Brief",
            "Generate concise, AI-powered summaries identifying key terms and obligations.",
            self.open_contract_brief
        )

        # Card 2: Q&A System
        card2 = self.create_feature_card(
            "Q&A System",
            "Ask complex questions and retrieve clause-level answers directly from your contract.",
            self.open_qa_page
        )

        # Card 3: Contract Diff
        card3 = self.create_feature_card(
            "Contract Diff",
            "Compare document versions with semantic alignment that ignores renumbering noise.",
            self.open_diff_page
        )

        card_layout.addWidget(card1)
        card_layout.addWidget(card2)
        card_layout.addWidget(card3)

        main_layout.addLayout(card_layout)

        # Footer
        footer = QLabel("ContractIQ | Intelligent Legal Solutions")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            color: #52067c; 
            margin-top: 50px; 
            font-size: 12px;
            background: transparent;
        """)
        main_layout.addWidget(footer)

    def open_contract_brief(self):
        from ui.contract_brief_page import ContractBriefPage
        self.page = ContractBriefPage()
        self.page.show()
        self.close()

    def open_qa_page(self):
        from ui.qa_page import QAPage
        self.page = QAPage()
        self.page.show()
        self.close()

    def open_diff_page(self):
        from ui.contract_diff_page import ContractDiffPage
        self.page = ContractDiffPage()
        self.page.show()
        self.close()

    # UPDATED: Removed 'icon' from the parameters
    def create_feature_card(self, title, description, callback):
        """Creates a styled interactive card for the home page dashboard."""

        # Container frame for the card
        card_frame = QFrame()
        card_frame.setFixedWidth(300)
        card_frame.setMinimumHeight(300) # Slightly reduced height since icons are gone
        card_frame.setStyleSheet("""
            QFrame {
                background-color: #380356;
                border-radius: 20px;
            }
            QFrame:hover {
                background-color: #4a0472;
                border: 2px solid #dcbdfb;
            }
        """)

        card_vbox = QVBoxLayout(card_frame)
        card_vbox.setContentsMargins(25, 40, 25, 40)
        card_vbox.setSpacing(20)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: white; background: transparent;")
        title_lbl.setAlignment(Qt.AlignCenter)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 15px; color: #dcbdfb; background: transparent; line-height: 1.4;")
        desc_lbl.setAlignment(Qt.AlignCenter)

        # Launch Button
        btn = QPushButton("Launch Tool")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #dcbdfb;
                color: #380356;
                border-radius: 10px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: white;
            }
        """)
        if callback:
            btn.clicked.connect(callback)

        card_vbox.addWidget(title_lbl)
        card_vbox.addWidget(desc_lbl)
        card_vbox.addStretch()
        card_vbox.addWidget(btn)

        return card_frame