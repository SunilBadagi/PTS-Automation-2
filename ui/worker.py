"""Background worker that runs the pipeline off the GUI thread.

All COM work (Excel + Minitab) happens here, so the window stays responsive.
Progress/log/finished are delivered to the UI via Qt signals (thread-safe).
"""

import pythoncom  # pyright: ignore[reportMissingImports]
from PyQt5.QtCore import QThread, pyqtSignal

from app.services.pipeline import Pipeline


class PipelineWorker(QThread):
    progress = pyqtSignal(int, str)   # percent, message
    log = pyqtSignal(str)             # log line
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.log.emit("Cancellation requested; stopping after current step...")

    def _is_cancelled(self):
        return self._cancelled

    def run(self):
        # COM must be initialised on this thread before any Dispatch call.
        pythoncom.CoInitialize()
        try:
            pipeline = Pipeline(
                progress=lambda pct, msg: self.progress.emit(int(pct), msg),
                log=lambda msg: self.log.emit(msg),
                is_cancelled=self._is_cancelled,
            )
            result = pipeline.run(self._config)
            self.finished.emit(result.success, result.message)
        except Exception as exc:  # noqa: BLE001 - never let the thread die silently
            self.finished.emit(False, f"Unexpected error: {exc}")
        finally:
            pythoncom.CoUninitialize()
