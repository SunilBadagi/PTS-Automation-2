"""Drive the PTS analyzer workbook (VBA macros) over Excel COM automation.

Designed so that Excel is *always* cleaned up -- even when a macro raises --
so the app never leaves orphaned EXCEL.EXE processes behind.
"""

import pythoncom  # pyright: ignore[reportMissingImports]
import win32com.client  # pyright: ignore[reportMissingImports]

from app.utils.logger import logger

MAIN_SHEET = "Main"


class PTSRunnerError(RuntimeError):
    """Raised when Excel automation fails."""


class PTSRunner:
    """Context manager around an Excel workbook.

    Usage::

        with PTSRunner(path, visible=True) as pts:
            pts.set_transfer_function_inputs(config)
            pts.run_macro("AllTempAnalysis")
            pts.save()
    """

    def __init__(self, workbook_path, visible: bool = True, keep_open: bool = False):
        self.workbook_path = str(workbook_path)
        self.visible = visible
        self.keep_open = keep_open
        self.excel = None
        self.wb = None

    # -- context manager -------------------------------------------------
    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close(save=False)
        return False  # never suppress exceptions

    # -- lifecycle -------------------------------------------------------
    def open(self):
        logger.info("Starting Excel")
        try:
            self.excel = win32com.client.DispatchEx("Excel.Application")
            self.excel.Visible = self.visible
            self.excel.DisplayAlerts = False
            self.excel.AskToUpdateLinks = False
            self.wb = self.excel.Workbooks.Open(self.workbook_path)
        except pythoncom.com_error as exc:
            self.close(save=False)
            raise PTSRunnerError(
                f"Could not open Excel workbook '{self.workbook_path}'. "
                f"Is Excel installed and the file valid?\n{exc}"
            ) from exc

        logger.info("Workbook opened: {}", self.wb.Name)
        return self

    def _main_sheet(self):
        try:
            return self.wb.Worksheets(MAIN_SHEET)
        except pythoncom.com_error as exc:
            raise PTSRunnerError(
                f"Worksheet '{MAIN_SHEET}' not found in the workbook."
            ) from exc

    # -- inputs ----------------------------------------------------------
    def set_transfer_function_inputs(self, config):
        sheet = self._main_sheet()
        sheet.Range("E3").Value = config.pressure_min
        sheet.Range("E4").Value = config.pressure_max
        sheet.Range("E5").Value = config.output_min
        sheet.Range("E6").Value = config.output_max
        sheet.Range("E7").Value = config.supply_voltage
        sheet.Range("E8").Value = config.pressure_az

    def set_pressure_unit(self, config):
        sheet = self._main_sheet()
        sheet.Range("F3").Value = config.pressure_unit
        sheet.Range("F4").Value = config.pressure_unit

    def set_sensor_type(self, config):
        sheet = self._main_sheet()
        sheet.Range("G3").Value = config.sensor_type
        sheet.Range("G4").Value = config.sensor_type

    def set_product_spec_inputs(self, config):
        sheet = self._main_sheet()
        sheet.Range("E12").Value = config.teb_limit
        sheet.Range("E13").Value = config.offset_limit
        sheet.Range("E14").Value = config.span_limit
        sheet.Range("E15").Value = config.linearity_limit
        sheet.Range("E16").Value = config.pressure_hyst
        sheet.Range("E17").Value = config.temp_hyst
        sheet.Range("E18").Value = config.accuracy

    def set_raw_data_path(self, raw_data_path):
        self._main_sheet().Range("AA1").Value = str(raw_data_path)

    def set_signal_type(self, value="Digital Output"):
        try:
            self._main_sheet().OLEObjects("ComboBox1").Object.Value = value
        except pythoncom.com_error:
            logger.warning("ComboBox1 not present; skipping signal type.")

    # -- execution -------------------------------------------------------
    def run_macro(self, macro_name):
        logger.info("Running macro: {}", macro_name)
        try:
            self.excel.Application.Run(macro_name)
        except pythoncom.com_error as exc:
            raise PTSRunnerError(
                f"Macro '{macro_name}' failed to run.\n{exc}"
            ) from exc

    def save(self):
        if self.wb is not None:
            self.wb.Save()
            logger.info("Workbook saved")

    def close(self, save: bool = False):
        """Close the workbook and quit Excel, swallowing cleanup errors."""
        if self.wb is not None:
            try:
                if not self.keep_open:
                    self.wb.Close(SaveChanges=save)
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                logger.warning("Error closing workbook: {}", exc)
            finally:
                self.wb = None

        if self.excel is not None and not self.keep_open:
            try:
                self.excel.Quit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error quitting Excel: {}", exc)
            finally:
                self.excel = None
                logger.info("Excel closed")
