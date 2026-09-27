import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox

from app.utils.logger import logger
from ui.main_window import MainWindow
from ui.theme import get_stylesheet


def _install_excepthook(app):
    """Show a dialog (and log) instead of silently crashing on an uncaught error."""

    def hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("Uncaught exception:\n{}", text)
        try:
            QMessageBox.critical(
                None, "Unexpected error",
                f"{exc_type.__name__}: {exc_value}\n\nSee console/log for details.",
            )
        except Exception:  # noqa: BLE001 - dialog itself may fail during teardown
            pass

    sys.excepthook = hook


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PTS Automation")
    app.setStyleSheet(get_stylesheet())
    _install_excepthook(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
