import os
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QFrame
from PySide6.QtCore import Qt


class LandingPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ContractIQ - Intelligent Legal Solutions")

        # Set main page background to dark purple [cite: 536]
        self.setStyleSheet("background-color: #1e1e1e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main Central Container
        central_container = QWidget()
        central_layout = QVBoxLayout(central_container)
        central_layout.setContentsMargins(100, 20, 100, 50)
        central_layout.setAlignment(Qt.AlignCenter)


        # Main Title
        title = QLabel("ContractIQ")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 82px; 
            font-weight: bold; 
            color: white; 
            letter-spacing: 3px;
            background: transparent;
        """)

        # Subtitle
        subtitle = QLabel("AI-Powered Contract Intelligence Platform")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 26px; 
            font-weight: 500; 
            color: #dcbdfb; 
            margin-top: 5px;
            background: transparent;
        """)

        # Description Card (Dark variant)
        desc_container = QFrame()
        desc_container.setFixedWidth(650)
        # Reduced margin-top to decrease space above the text
        desc_container.setStyleSheet("""
            QFrame {
                background-color: #2a0242;
                border-radius: 15px;
                border: 1px solid #52067c;
                margin-top: 20px;
            }
        """)

        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(40, 30, 40, 30)

        desc_text = QLabel(
            "Extract clauses, analyze obligations, compare document versions,\n"
            "and query agreements using natural language — all in one place."
        )
        desc_text.setAlignment(Qt.AlignCenter)
        desc_text.setWordWrap(True)
        desc_text.setStyleSheet("""
            font-size: 17px; 
            color: #dcbdfb; 
            line-height: 1.6; 
            border: none;
            background: transparent;
        """)
        desc_layout.addWidget(desc_text)

        start_btn = QPushButton("Get Started →")
        start_btn.setFixedWidth(280)
        start_btn.setMinimumHeight(60) # Explicit minimum height to prevent "broken" visualization
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #dcbdfb;
                color: #1a012a;
                border-radius: 30px;
                font-size: 19px;
                font-weight: bold;
                margin-top: 40px;
                border: none;
            }
            QPushButton:hover {
                background-color: white;
                color: #1a012a;
            }
        """)
        start_btn.clicked.connect(self.open_home)

        # Add components to layout
        # Replaced top stretch with fixed spacing to control exactly where the content starts
        central_layout.addSpacing(120)
        central_layout.addWidget(title)
        central_layout.addWidget(subtitle)
        central_layout.addWidget(desc_container, 0, Qt.AlignCenter)
        central_layout.addWidget(start_btn, 0, Qt.AlignCenter)
        central_layout.addStretch()

        # Footer
        footer = QLabel("Empowering legal teams with precision AI.")
        footer.setAlignment(Qt.AlignCenter)
        # Updated color to #dcbdfb for better visibility on dark background
        footer.setStyleSheet("""
            color: #dcbdfb; 
            padding-bottom: 40px; 
            font-size: 14px; 
            font-style: italic;
            background: transparent;
        """)

        layout.addWidget(central_container)
        layout.addWidget(footer)


    def open_home(self):
        from ui.home_page import HomePage
        self.home = HomePage()
        self.home.show()
        self.close()