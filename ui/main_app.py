import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile
from ui.landing_page import LandingPage
from ui.styles import APP_STYLE


def main():
    app = QApplication(sys.argv)

    QWebEngineProfile.defaultProfile()
    app.setStyleSheet(APP_STYLE)

    window = LandingPage()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()