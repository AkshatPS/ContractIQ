from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt


class LandingPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ContractIQ")
        self.showMaximized()

        layout = QVBoxLayout()
        layout.setContentsMargins(100, 100, 100, 100)
        layout.setSpacing(20)

        # Title
        title = QLabel("ContractIQ")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        # Subtitle
        subtitle = QLabel("AI-powered Contract Intelligence Platform")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        # Description
        desc = QLabel(
            "Extract clauses, analyze agreements, compare contracts,\n"
            "and ask intelligent questions — all in one place."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 16px; color: #aaaaaa;")

        # CTA Button
        btn = QPushButton("Get Started →")
        btn.setFixedHeight(50)
        btn.clicked.connect(self.open_home)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(desc)
        layout.addSpacing(30)
        layout.addWidget(btn)
        layout.addStretch()

        self.setLayout(layout)

    def open_home(self):
        from ui.home_page import HomePage

        self.home = HomePage()
        self.home.show()
        self.close()