"""Configuration tab: PTS inputs, graph configuration, and run controls."""

from pathlib import Path

from PyQt5.QtCore import Qt, QEvent, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QTextCursor
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListView, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.config import settings
from app.models.graph_config import (
    DEFAULT_HISTOGRAM_METRICS, DEFAULT_SCATTER_METRICS, DEFAULT_TEB_RANGES,
    CPK_METRICS, GraphConfig, TEBRange, format_teb_ranges, parse_teb_ranges,
)
from app.models.pipeline_config import PipelineConfig
from app.models.pts_config import ASIC_OPTIONS, PTSConfig
from ui.worker import PipelineWorker

PTS_DEFAULTS = {
    "pressure_min": "0", "pressure_max": "1",
    "output_min": "10", "output_max": "90",
    "supply_voltage": "3.3", "pressure_az": "0",
    "teb_limit": "3", "offset_limit": "2",
    "span_limit": "2", "linearity_limit": "0.2",
    "pressure_hyst": "0.18", "temp_hyst": "1.1",
    "accuracy": "0.25",
}


class CheckableComboBox(QComboBox):
    """A compact multi-select dropdown whose items have checkboxes."""

    def __init__(self, items, checked=None, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.setMinimumWidth(280)
        self.setModel(QStandardItemModel(self))
        view = QListView()
        view.setSelectionMode(QListView.NoSelection)
        self.setView(view)
        self.view().viewport().installEventFilter(self)
        checked = set(checked or [])
        for label, value in items:
            item = QStandardItem(label)
            item.setData(value, Qt.UserRole)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if value in checked else Qt.Unchecked)
            self.model().appendRow(item)
        self.model().itemChanged.connect(lambda _: self._refresh_text())
        self._refresh_text()

    def eventFilter(self, watched, event):
        if watched is self.view().viewport() and event.type() == QEvent.MouseButtonPress:
            index = self.view().indexAt(event.pos())
            if index.isValid():
                item = self.model().itemFromIndex(index)
                item.setCheckState(
                    Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                )
                self._refresh_text()
                return True
        return super().eventFilter(watched, event)

    def checked_values(self):
        return [
            self.model().item(row).data(Qt.UserRole)
            for row in range(self.model().rowCount())
            if self.model().item(row).checkState() == Qt.Checked
        ]

    def _refresh_text(self):
        labels = [
            self.model().item(row).text()
            for row in range(self.model().rowCount())
            if self.model().item(row).checkState() == Qt.Checked
        ]
        self.setCurrentText(", ".join(labels) if labels else "Select metrics")
TRANSFER_KEYS = [
    "pressure_min", "pressure_max", "output_min",
    "output_max", "supply_voltage", "pressure_az",
]
SPEC_KEYS = [
    "teb_limit", "offset_limit", "span_limit",
    "linearity_limit", "pressure_hyst", "temp_hyst", "accuracy",
]


class ConfigTab(QWidget):
    runStarted = pyqtSignal()
    runFinished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.inputs = {}
        self._build_ui()

    # -- UI construction -------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(12)

        self.layout.addWidget(self._build_paths_group())
        self.layout.addWidget(self._build_asic_group())
        self.layout.addWidget(self._build_transfer_group())
        self.layout.addWidget(self._build_spec_group())
        # self.layout.addWidget(self._build_descriptor_group())
        self.layout.addWidget(self._build_graph_group())
        self.layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_run_panel())

    def _build_paths_group(self):
        group = QGroupBox("File Paths")
        form = QFormLayout(group)

        self.csv_input = QLineEdit(str(settings.RAW_DATA))
        form.addRow("Upload Char Data CSV:", self._path_row(self.csv_input, self._browse_csv))

        # self.analyzer_input = QLineEdit(str(settings.PTS_ANALYZER))
        # form.addRow(
        #     "PTS Analyzer (.xlsm):",
        #     self._path_row(self.analyzer_input, self._browse_analyzer),
        # )

        self.project_input = QLineEdit(str(settings.PROJECT_FILE.parent))
        form.addRow(
            "Save output files in:",
            self._path_row(self.project_input, self._browse_project),
        )
        return group

    def _path_row(self, line_edit, handler):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("Browse")
        btn.clicked.connect(handler)
        row.addWidget(line_edit)
        row.addWidget(btn)
        wrapper = QWidget()
        wrapper.setLayout(row)
        return wrapper

    def _build_transfer_group(self):
        group = QGroupBox("Transfer Function Inputs")
        form = QFormLayout(group)
        for key in TRANSFER_KEYS:
            le = QLineEdit(PTS_DEFAULTS[key])
            self.inputs[key] = le
            form.addRow(self._label(key), le)
        return group

    def _build_asic_group(self):
        group = QGroupBox("ASIC Conversion")
        form = QFormLayout(group)
        self.asic_type = QComboBox()
        self.asic_type.addItems(ASIC_OPTIONS)
        form.addRow("ASIC type:", self.asic_type)
        return group

    def _build_spec_group(self):
        group = QGroupBox("Product Spec Limits")
        form = QFormLayout(group)
        for key in SPEC_KEYS:
            le = QLineEdit(PTS_DEFAULTS[key])
            self.inputs[key] = le
            form.addRow(self._label(key), le)
        # group = QGroupBox("Descriptors")
        # form = QFormLayout(group)

        self.sensor_type = QComboBox()
        self.sensor_type.setEditable(True)
        self.sensor_type.addItems(["differential", "absolute", "gauge"])
        form.addRow("Sensor Type:", self.sensor_type)
        self.pressure_unit = QComboBox()
        self.pressure_unit.setEditable(True)
        self.pressure_unit.addItems(["inH2O", "psi", "bar", "kPa", "mbar"])
        form.addRow("Pressure Unit:", self.pressure_unit)
        return group

    def _build_descriptor_group(self):
        group = QGroupBox("Descriptors")
        form = QFormLayout(group)

        self.sensor_type = QComboBox()
        self.sensor_type.setEditable(True)
        self.sensor_type.addItems(["differential", "absolute", "gauge"])
        form.addRow("Sensor Type:", self.sensor_type)

        self.pressure_unit = QComboBox()
        self.pressure_unit.setEditable(True)
        self.pressure_unit.addItems(["inH2O", "psi", "bar", "kPa", "mbar"])
        form.addRow("Pressure Unit:", self.pressure_unit)
        return group

    def _build_graph_group(self):
        group = QGroupBox("Graph Configuration (Minitab)")
        form = QFormLayout(group)

        self.run_minitab_cb = QCheckBox("Run Minitab")
        self.run_minitab_cb.setChecked(True)
        # form.addRow(self.run_minitab_cb)

        # Which graphs
        self.cb_scatter = QCheckBox("Temperature scatter")
        self.cb_scatter.setChecked(True)
        self.cb_histogram = QCheckBox("Histogram")
        self.cb_histogram.setChecked(True)
        self.cb_distribution = QCheckBox("Distribution ID")
        self.cb_distribution.setChecked(True)
        self.cb_cpk = QCheckBox("Cpk / Capability")
        self.cb_cpk.setChecked(True)
        graphs_row = QHBoxLayout()
        for cb in (self.cb_scatter, self.cb_histogram,
                   self.cb_distribution, self.cb_cpk):
            graphs_row.addWidget(cb)
        graphs_row.addStretch(1)
        graphs_wrap = QWidget()
        graphs_wrap.setLayout(graphs_row)
        form.addRow("Graphs:", graphs_wrap)

        # Metrics per graph
        scatter_options = [(metric, metric) for metric in DEFAULT_SCATTER_METRICS]
        self.scatter_metrics = CheckableComboBox(
            scatter_options, DEFAULT_SCATTER_METRICS
        )
        form.addRow("Scatter metrics:", self.scatter_metrics)

        histogram_options = [
            ("TEB @(0-50)", "TEB @(0-50)"),
            ("TEB @(-20 - 85)", "TEB @(-20 - 85)"),
            ("TEB @(-40 - 110)", "TEB @(-40 - 110)"),
            ("Accuracy", "Accuracy Error"),
        ]
        self.histogram_metrics = CheckableComboBox(
            histogram_options, DEFAULT_HISTOGRAM_METRICS
        )
        form.addRow("Histogram metrics:", self.histogram_metrics)

        teb_options = [(item.name, item.name) for item in DEFAULT_TEB_RANGES]
        self.teb_range_metrics = CheckableComboBox(
            teb_options, [item.name for item in DEFAULT_TEB_RANGES]
        )
        form.addRow("TEB ranges:", self.teb_range_metrics)

        # Cpk spec limits
        cpk_options = [("Accuracy", "Accuracy Error") if metric == "Accuracy Error"
                       else (metric, metric) for metric in CPK_METRICS]
        self.cpk_metrics = CheckableComboBox(cpk_options, [CPK_METRICS[0]])
        form.addRow("Cpk metrics:", self.cpk_metrics)
        self.cpk_usl_fields = {}
        self.cpk_usl_rows = {}
        self.cpk_usl_layout = QVBoxLayout()
        self.cpk_usl_layout.setContentsMargins(0, 0, 0, 0)
        cpk_usl_wrap = QWidget()
        cpk_usl_wrap.setLayout(self.cpk_usl_layout)
        form.addRow("USL per metric:", cpk_usl_wrap)
        self.cpk_metrics.model().itemChanged.connect(
            lambda _: self._refresh_cpk_usl_fields()
        )
        self._refresh_cpk_usl_fields()

        hint = QLabel(
            "Metrics/columns must match the header names in the extracted "
            "Data / Stacked Data sheets."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        form.addRow(hint)
        return group

    def _build_run_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Generate Minitab Report")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.start_pipeline)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_pipeline)

        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(lambda: self.log_console.clear())

        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.clear_log_btn)
        layout.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("%p%  -  Idle")
        layout.addWidget(self.progress)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(150)
        layout.addWidget(self.log_console)
        return panel

    def _label(self, key):
        return key.replace("_", " ").title() + ":"

    # -- browse handlers -------------------------------------------------
    def _browse_csv(self):
        name, _ = QFileDialog.getOpenFileName(
            self, "Select CSV", str(settings.INPUT_DIR), "CSV Files (*.csv)"
        )
        if name:
            self.csv_input.setText(name)

    def _browse_analyzer(self):
        name, _ = QFileDialog.getOpenFileName(
            self, "Select PTS Analyzer", str(settings.INPUT_DIR),
            "Excel Macro Workbook (*.xlsm *.xlsb *.xls)"
        )
        if name:
            self.analyzer_input.setText(name)

    def _browse_project(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select output folder", self.project_input.text().strip()
        )
        if directory:
            self.project_input.setText(directory)

    # -- config assembly -------------------------------------------------
    def _parse_float_list(self, text, field_name):
        items = []
        for token in text.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                items.append(float(token))
            except ValueError:
                raise ValueError(
                    f"'{field_name}' contains a non-number: '{token}'."
                )
        return items

    def _parse_str_list(self, text):
        return [t.strip() for t in text.split(",") if t.strip()]

    def _optional_float(self, text):
        text = text.strip()
        if not text:
            return float("nan")
        return float(text)

    def _refresh_cpk_usl_fields(self):
        selected = self.cpk_metrics.checked_values()
        # Remove rows for deselected metrics
        for metric in list(self.cpk_usl_rows.keys()):
            if metric not in selected:
                row_widget = self.cpk_usl_rows.pop(metric)
                self.cpk_usl_layout.removeWidget(row_widget)
                row_widget.hide()
                row_widget.deleteLater()
                self.cpk_usl_fields.pop(metric, None)
        # Add rows for newly selected metrics
        for metric in selected:
            if metric in self.cpk_usl_rows:
                continue
            label_text = "Accuracy" if metric == "Accuracy Error" else metric
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.addWidget(QLabel(f"{label_text}  USL:"))
            usl = QLineEdit("3")
            usl.setPlaceholderText("e.g. 3.0")
            usl.setMaximumWidth(100)
            row_layout.addWidget(usl)
            row_layout.addStretch(1)
            self.cpk_usl_layout.addWidget(row)
            self.cpk_usl_rows[metric] = row
            self.cpk_usl_fields[metric] = usl

    def build_config(self):
        pts_values = {k: le.text() for k, le in self.inputs.items()}
        pts_values["sensor_type"] = self.sensor_type.currentText()
        pts_values["pressure_unit"] = self.pressure_unit.currentText()
        pts_values["asic_type"] = self.asic_type.currentText()
        pts = PTSConfig.from_dict(pts_values)

        graph = GraphConfig(
            enable_scatter=self.cb_scatter.isChecked(),
            enable_histogram=self.cb_histogram.isChecked(),
            enable_distribution_id=self.cb_distribution.isChecked(),
            enable_cpk=self.cb_cpk.isChecked(),
            scatter_metrics=self.scatter_metrics.checked_values(),
            histogram_metrics=self.histogram_metrics.checked_values(),
            teb_ranges=[
                item for item in DEFAULT_TEB_RANGES
                if item.name in self.teb_range_metrics.checked_values()
            ],
            cpk_column=self.cpk_metrics.checked_values()[0]
            if self.cpk_metrics.checked_values() else "",
            cpk_usl=3.0,
            cpk_metrics=self.cpk_metrics.checked_values(),
            cpk_usls={
                metric: self._optional_float(self.cpk_usl_fields[metric].text())
                for metric in self.cpk_metrics.checked_values()
            },
        )

        output_dir = Path(self.project_input.text().strip())
        config = PipelineConfig(
            pts=pts,
            graph=graph,
            raw_data=self.csv_input.text().strip(),
            pts_analyzer=str(settings.PTS_ANALYZER),
            processed_input=output_dir / settings.PROCESSED_INPUT.name,
            data_output=output_dir / settings.DATA_OUTPUT.name,
            stacked_output=output_dir / settings.STACKED_OUTPUT.name,
            project_file=output_dir / settings.PROJECT_FILE.name,
            distribution_rtf=output_dir / settings.DISTRIBUTION_RTF.name,
            run_minitab=self.run_minitab_cb.isChecked(),
        )
        return config

    # -- run lifecycle ---------------------------------------------------
    def start_pipeline(self):
        try:
            config = self.build_config()
        except Exception as exc:  # ConfigError / ValueError from parsing
            QMessageBox.warning(self, "Invalid configuration", str(exc))
            return

        self._set_running(True)
        self.progress.setValue(0)
        self._append_log("=== Pipeline started ===")

        self.worker = PipelineWorker(config)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._append_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        self.runStarted.emit()

    def cancel_pipeline(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, pct, msg):
        self.progress.setValue(pct)
        self.progress.setFormat(f"%p%  -  {msg}")

    def _append_log(self, msg):
        self.log_console.appendPlainText(msg)
        self.log_console.moveCursor(QTextCursor.End)

    def _on_finished(self, success, message):
        self._append_log(f"=== {'DONE' if success else 'FAILED'}: {message} ===")
        self._set_running(False)
        if success:
            self.progress.setFormat("%p%  -  Complete")
            QMessageBox.information(self, "Success", message)
        else:
            self.progress.setFormat("%p%  -  Stopped")
            QMessageBox.critical(self, "Pipeline failed", message)
        self.runFinished.emit(success, message)
        self.worker = None

    def _set_running(self, running):
        self.run_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
