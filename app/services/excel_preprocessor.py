"""Turn the raw chamber CSV into a clean .xlsx the PTS analyzer can import.

Robust against the two known CSV shapes:
  * a leading part-number line before the header row, and
  * a header row on line 1 with no part-number line.
The pressure value is always read from CSV column H (the eighth column), even
when the chamber software changes the column header.
"""

import csv

import pandas as pd

from app.models.pts_config import ASIC_3224, ASIC_ELMOS, ASIC_OPTIONS
from app.utils.logger import logger

PRESSURE_COLUMN_INDEX = 7  # CSV column H, using zero-based indexing.
# The chamber emits a header row containing these tokens; used to detect whether
# line 1 is a header or a part-number banner.
HEADER_MARKERS = ("Serial Number", "Temp Setpoint", "Pressure Output")


class PreprocessError(RuntimeError):
    """Raised when the raw CSV cannot be understood."""


class ExcelPreprocessor:
    def _looks_like_header(self, line: str) -> bool:
        return any(marker in line for marker in HEADER_MARKERS)

    def process(self, input_file, output_file, asic_type=ASIC_ELMOS):
        input_file = str(input_file)
        logger.info("Reading raw chamber file: {}", input_file)

        try:
            with open(input_file, "r", newline="", encoding="utf-8-sig") as f:
                first_line = f.readline().strip()
        except OSError as exc:
            raise PreprocessError(f"Could not open CSV: {exc}") from exc

        if not first_line:
            raise PreprocessError("CSV file is empty.")

        # Decide whether line 1 is a part-number banner or the header row itself.
        if self._looks_like_header(first_line):
            part_number = ""
            skiprows = 0
            logger.info("No part-number banner; header is on line 1.")
        else:
            # First cell of the banner line is the part number.
            part_number = next(csv.reader([first_line]), [""])[0].strip()
            skiprows = 1
            logger.info("Part Number: {}", part_number or "<blank>")

        try:
            df = pd.read_csv(input_file, skiprows=skiprows)
        except Exception as exc:  # pandas raises a variety of parser errors
            raise PreprocessError(f"Could not parse CSV rows: {exc}") from exc

        if df.empty:
            raise PreprocessError("CSV contains a header but no data rows.")

        # The chamber's pressure output is always in CSV column H.
        pressure_col = self._find_pressure_column(df)

        df[pressure_col] = pd.to_numeric(df[pressure_col], errors="coerce")
        df[pressure_col] = self._convert_pressure(df[pressure_col], asic_type)

        self._write_workbook(df, part_number, output_file)

        logger.info("Processed {} rows -> {}", len(df), output_file)
        return output_file

    def _convert_pressure(self, pressure_counts, asic_type):
        if asic_type == ASIC_3224:
            logger.info("Converting pressure counts using ASIC 3224 formula.")
            return pressure_counts / (2 ** 24) * 100
        if asic_type == ASIC_ELMOS:
            logger.info("Converting pressure counts using ELMOS formula.")
            return (32000 + pressure_counts) / 640
        raise PreprocessError(
            f"Unsupported ASIC conversion '{asic_type}'. "
            f"Choose one of: {', '.join(ASIC_OPTIONS)}"
        )

    def _find_pressure_column(self, df: pd.DataFrame) -> str:
        if len(df.columns) <= PRESSURE_COLUMN_INDEX:
            raise PreprocessError(
                "CSV does not contain pressure column H (the eighth column). "
                f"Available columns: {list(df.columns)}"
            )
        return df.columns[PRESSURE_COLUMN_INDEX]

    def _write_workbook(self, df, part_number, output_file):
        try:
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                pd.DataFrame([[part_number]]).to_excel(
                    writer, sheet_name="Processed Input", index=False,
                    header=False, startrow=0
                )
                df.to_excel(
                    writer, sheet_name="Processed Input", index=False, startrow=1
                )
        except PermissionError as exc:
            raise PreprocessError(
                f"Cannot write '{output_file}'. Is it open in Excel? ({exc})"
            ) from exc
