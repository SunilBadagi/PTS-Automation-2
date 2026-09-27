"""Thin wrapper around the Minitab COM automation object.

Raises :class:`MinitabUnavailable` (instead of a raw COM error) when Minitab is
not installed/registered, so the pipeline can skip graphing gracefully.
"""

import time
from pathlib import Path

import pandas as pd
import pythoncom  # pyright: ignore[reportMissingImports]
import win32com.client  # pyright: ignore[reportMissingImports]

from app.utils.logger import logger


class MinitabUnavailable(RuntimeError):
    """Raised when the Minitab COM server cannot be created."""


class MinitabError(RuntimeError):
    """Raised when a Minitab operation fails."""


class MinitabService:
    def __init__(self):
        try:
            self.mtb = win32com.client.Dispatch("Mtb.Application")
        except pythoncom.com_error as exc:
            raise MinitabUnavailable(
                "Could not start Minitab (Mtb.Application). "
                "Is Minitab installed on this machine?"
            ) from exc

        try:
            self.project = self.mtb.ActiveProject
            self.ws = self.project.ActiveWorksheet
        except pythoncom.com_error as exc:
            raise MinitabError(f"Could not access active Minitab project: {exc}") from exc

    # -- worksheets ------------------------------------------------------
    def clear_worksheet(self, ws):
        while ws.Columns.Count > 0:
            ws.Columns.Item(1).Delete()

    def create_worksheet(self, name):
        ws = self.project.Worksheets.Add()
        ws.Name = name
        return ws

    def activate_worksheet(self, worksheet_name):
        for i in range(1, self.project.Worksheets.Count + 1):
            ws = self.project.Worksheets.Item(i)
            if ws.Name == worksheet_name:
                self.project.ActiveWorksheet = ws
                return ws
        raise MinitabError(f"Worksheet not found: {worksheet_name}")

    def get_active_worksheet(self):
        return self.project.ActiveWorksheet

    def load_dataframe(self, df, ws):
        self.clear_worksheet(ws)
        for column_name in df.columns:
            col = ws.Columns.Add()
            col.Name = str(column_name)
            series = df[column_name]

            if pd.api.types.is_numeric_dtype(series):
                values = [
                    "*" if pd.isna(v) else float(v) for v in series
                ]
            else:
                values = [
                    "" if pd.isna(v) else str(v) for v in series
                ]
            col.SetData(values)

        logger.info(
            "Worksheet '{}' loaded: {} cols x {} rows",
            ws.Name, len(df.columns), len(df),
        )

    # -- commands / graphs ----------------------------------------------
    def execute(self, command):
        try:
            self.project.ExecuteCommand(command)
        except pythoncom.com_error as exc:
            raise MinitabError(
                f"Minitab command failed:\n{command.strip()}\n{exc}"
            ) from exc

    def save_last_graph(self, output_path):
        cmd = self.project.Commands.Item(self.project.Commands.Count)
        output = cmd.Outputs.Item(1)
        graph = output.Graph
        output_path = str(Path(output_path).resolve())
        graph.SaveAs(output_path)
        logger.info("Graph saved: {}", output_path)

    def save_command_output(self, output_path):
        """Save the last command's output document (e.g. distribution report).

        Scans commands from newest to oldest for one that exposes an
        OutputDocument, instead of assuming a fixed command index.
        """
        output_path = str(Path(output_path).resolve())
        for i in range(self.project.Commands.Count, 0, -1):
            cmd = self.project.Commands.Item(i)
            try:
                doc = cmd.OutputDocument
            except pythoncom.com_error:
                continue
            if doc is None:
                continue
            try:
                doc.SaveAs(output_path)
                logger.info("Output document saved: {}", output_path)
                return True
            except pythoncom.com_error as exc:
                logger.warning("Could not save output document: {}", exc)
                return False
        logger.warning("No command with an output document was found to save.")
        return False

    def save_project(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            p = p.with_name(f"{p.stem}_{timestamp}{p.suffix}")
        try:
            self.project.SaveAs(str(p))
        except pythoncom.com_error as exc:
            raise MinitabError(f"Could not save Minitab project: {exc}") from exc
        logger.info("Project saved: {}", p)
        return p
