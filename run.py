import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from ui.landing_page import LandingPage
from ui.styles import APP_STYLE


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    window = LandingPage()
    window.show()

    QTimer.singleShot(0, window.showMaximized)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()