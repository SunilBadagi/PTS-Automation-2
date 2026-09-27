"""Merge the per-run Data / Stacked Data sheets into one master workbook.

Characterisation is done in batches (e.g. 30 or 60 sensors per chamber run)
because of hardware limits. Each run goes through the PTS analyzer on its own;
this service stacks the resulting sheets so the whole population (100-200
sensors) can be analysed and graphed in Minitab as one data set.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd

from app.services.pts_extractor import DATA_SHEET, STACKED_SHEET
from app.utils.logger import logger

RUN_COLUMN = "Char Run"
SUMMARY_SHEET = "Run Summary"
SERIAL_COLUMN = "Serial Number"


class MergeError(RuntimeError):
    """Raised when the per-run sheets cannot be merged."""


@dataclass
class RunOutput:
    """One analysed char run: its label, source file and per-run workbook."""
    label: str
    source: Path
    workbook: Path


class RunMerger:
    def merge(self, runs: List[RunOutput], destination) -> List[str]:
        """Write the merged sheets to ``destination``; return any warnings."""
        if not runs:
            raise MergeError("No analysed runs to merge.")

        data_frames, stacked_frames, summary = [], [], []
        for run in runs:
            data_df = self._read(run, DATA_SHEET)
            stacked_df = self._read(run, STACKED_SHEET)
            data_frames.append(self._tag(data_df, run.label))
            stacked_frames.append(self._tag(stacked_df, run.label))
            summary.append({
                RUN_COLUMN: run.label,
                "Source File": str(run.source),
                "Run Workbook": str(run.workbook),
                "Sensors (Data rows)": len(data_df),
                "Stacked Data rows": len(stacked_df),
            })

        # sort=False keeps the analyzer's column order; a column missing from
        # one run is filled with blanks rather than dropping data.
        data = pd.concat(data_frames, ignore_index=True, sort=False)
        stacked = pd.concat(stacked_frames, ignore_index=True, sort=False)

        warnings = self._check_duplicate_serials(data)

        try:
            with pd.ExcelWriter(destination, engine="openpyxl", mode="w") as writer:
                data.to_excel(writer, sheet_name=DATA_SHEET, index=False)
                stacked.to_excel(writer, sheet_name=STACKED_SHEET, index=False)
                pd.DataFrame(summary).to_excel(
                    writer, sheet_name=SUMMARY_SHEET, index=False
                )
        except PermissionError as exc:
            raise MergeError(
                f"Cannot write '{destination}'. Is it open in Excel? ({exc})"
            ) from exc

        logger.info(
            "Merged {} run(s): {} Data rows, {} Stacked Data rows -> {}",
            len(runs), len(data), len(stacked), destination,
        )
        return warnings

    def _read(self, run: RunOutput, sheet):
        try:
            return pd.read_excel(run.workbook, sheet_name=sheet)
        except Exception as exc:  # noqa: BLE001
            raise MergeError(
                f"Could not read '{sheet}' for run '{run.label}' "
                f"from '{run.workbook}': {exc}"
            ) from exc

    @staticmethod
    def _tag(df, label):
        df = df.copy()
        df.insert(0, RUN_COLUMN, label)
        return df

    @staticmethod
    def _check_duplicate_serials(data) -> List[str]:
        """Serial numbers repeated across runs would merge in the scatter plots."""
        if SERIAL_COLUMN not in data.columns:
            return []
        per_serial = data.dropna(subset=[SERIAL_COLUMN]).groupby(SERIAL_COLUMN)[
            RUN_COLUMN
        ].nunique()
        repeated = sorted(str(s) for s in per_serial[per_serial > 1].index)
        if not repeated:
            return []
        shown = ", ".join(repeated[:10]) + (" ..." if len(repeated) > 10 else "")
        return [
            f"{len(repeated)} serial number(s) appear in more than one run "
            f"({shown}); use the '{RUN_COLUMN}' column to tell them apart."
        ]
