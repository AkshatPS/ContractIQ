from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt


class HomePage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ContractIQ - Home")
        self.showMaximized()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(80, 60, 80, 60)

        # Title
        title = QLabel("Choose a Feature")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Powerful AI tools to analyze your contracts")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        # Horizontal layout for cards
        card_layout = QHBoxLayout()
        card_layout.setSpacing(30)

        # Cards
        card1 = self.create_card(
            "Contract Brief",
            "Generate concise summaries",
            self.open_contract_brief
        )
        card2 = self.create_card(
            "Q&A System",
            "Ask questions from contracts",
            self.open_qa_page
        )

        card3 = self.create_card(
            "Contract Diff",
            "Compare agreements intelligently",
            self.open_diff_page
        )

        card1.setMinimumWidth(250)
        card2.setMinimumWidth(250)
        card3.setMinimumWidth(250)

        # Add cards side by side
        card_layout.addWidget(card1)
        card_layout.addWidget(card2)
        card_layout.addWidget(card3)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addSpacing(50)
        main_layout.addLayout(card_layout)

        self.setLayout(main_layout)

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

    def create_card(self, title, description, callback):
        btn = QPushButton(f"{title}\n\n{description}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("card")
        btn.setMinimumHeight(180)

        if callback:
            btn.clicked.connect(callback)

        return btn