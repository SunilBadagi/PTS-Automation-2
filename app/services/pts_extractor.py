"""Extract the 'Data' and 'Stacked Data' sheets produced by the PTS analyzer."""

import pandas as pd

from app.utils.logger import logger

DATA_SHEET = "Data"
STACKED_SHEET = "Stacked Data"


class ExtractError(RuntimeError):
    """Raised when the expected analyzer output sheets cannot be read."""


class PTSExtractor:
    def extract(self, workbook, output_data, output_stacked):
        workbook = str(workbook)
        self._extract_sheet(workbook, DATA_SHEET, output_data, DATA_SHEET)
        self._extract_sheet(workbook, STACKED_SHEET, output_stacked, STACKED_SHEET)

    def _extract_sheet(self, workbook, sheet_name, destination, output_sheet):
        logger.info("Extracting sheet '{}'", sheet_name)
        try:
            df = pd.read_excel(workbook, sheet_name=sheet_name)
        except ValueError as exc:
            # openpyxl/pandas raise ValueError when a sheet is missing.
            raise ExtractError(
                f"Sheet '{sheet_name}' not found in '{workbook}'. "
                "Did the PTS macros complete successfully?"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ExtractError(
                f"Could not read sheet '{sheet_name}': {exc}"
            ) from exc

        try:
            with pd.ExcelWriter(
                destination, engine="openpyxl", mode="a", if_sheet_exists="replace"
            ) as writer:
                df.to_excel(writer, sheet_name=output_sheet, index=False)
        except PermissionError as exc:
            raise ExtractError(
                f"Cannot write '{destination}'. Is it open in Excel? ({exc})"
            ) from exc
        logger.info("Wrote {} rows to {}", len(df), destination)
