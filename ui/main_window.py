"""Main application window.

The embedded Excel/Minitab ActiveX views are loaded lazily and guarded with
try/except, so the app always launches -- even on a machine without Excel or
Minitab registered -- and a failed embed shows a friendly message instead of
crashing the process.
"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app.config.settings import PTS_ANALYZER
from ui.config_tab import ConfigTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PTS Automation")
        self.resize(1080, 860)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.config_tab = ConfigTab()
        self.config_tab.runStarted.connect(self._on_run_started)
        self.config_tab.runFinished.connect(self._on_run_finished)
        self.tabs.addTab(self.config_tab, "Configuration")

        # Lazy ActiveX tabs.
        self._excel_loaded = False
        self._minitab_loaded = False
        self.excel_tab = self._make_lazy_tab(
            "Embed the PTS analyzer workbook in this tab.",
            self._load_excel,
        )
        self.tabs.addTab(self.excel_tab, "PTS Analyser (Excel)")

        self.minitab_tab = self._make_lazy_tab(
            "Embed the Minitab application in this tab.",
            self._load_minitab,
        )
        self.tabs.addTab(self.minitab_tab, "Minitab")

        self.statusBar().showMessage("Ready")

    # -- lazy tab scaffolding -------------------------------------------
    def _make_lazy_tab(self, description, loader):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel(description)
        label.setObjectName("hint")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn = QPushButton("Load embedded view")
        btn.setObjectName("primary")
        btn.setMaximumWidth(220)
        btn.clicked.connect(loader)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        tab._content_layout = layout  # stash for the loader
        return tab

    def _replace_tab_content(self, tab, widget):
        layout = tab._content_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(widget)

    def _show_tab_error(self, tab, message):
        label = QLabel(message)
        label.setObjectName("hint")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        self._replace_tab_content(tab, label)

    # -- ActiveX loaders (guarded) --------------------------------------
    def _load_excel(self):
        if self._excel_loaded:
            return
        try:
            from PyQt5.QAxContainer import QAxWidget
            widget = QAxWidget()
            if os.path.exists(str(PTS_ANALYZER)):
                widget.setControl(str(PTS_ANALYZER))
            else:
                widget.setControl("Excel.Application")
            self._replace_tab_content(self.excel_tab, widget)
            self._excel_loaded = True
            self.statusBar().showMessage("Excel view loaded", 4000)
        except Exception as exc:  # noqa: BLE001
            self._show_tab_error(
                self.excel_tab,
                "Could not embed Excel.\n"
                "Excel may not be installed or ActiveX embedding is blocked.\n\n"
                f"Details: {exc}",
            )

    def _load_minitab(self):
        if self._minitab_loaded:
            return
        try:
            from PyQt5.QAxContainer import QAxWidget
            widget = QAxWidget("Mtb.Application")
            self._replace_tab_content(self.minitab_tab, widget)
            self._minitab_loaded = True
            self.statusBar().showMessage("Minitab view loaded", 4000)
        except Exception as exc:  # noqa: BLE001
            self._show_tab_error(
                self.minitab_tab,
                "Could not embed Minitab.\n"
                "Minitab may not be installed on this machine.\n\n"
                f"Details: {exc}",
            )

    # -- run state feedback ---------------------------------------------
    def _on_run_started(self):
        self.statusBar().showMessage("Pipeline running...")

    def _on_run_finished(self, success, message):
        state = "completed" if success else "failed"
        self.statusBar().showMessage(f"Pipeline {state}: {message}", 8000)

    def closeEvent(self, event):
        # Don't let the user close the window mid-run and orphan a COM process.
        worker = getattr(self.config_tab, "worker", None)
        if worker is not None and worker.isRunning():
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Pipeline running",
                "The pipeline is still running. Cancel it and quit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            worker.cancel()
            worker.wait(5000)
        event.accept()
