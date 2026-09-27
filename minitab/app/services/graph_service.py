"""Minitab graph builders, driven by a GraphConfig from the UI."""

import math

from app.models.graph_config import X_TEMPERATURE, SERIES_COLUMN
from app.utils.logger import logger


class GraphService:
    def __init__(self, mtb):
        self.mtb = mtb

    def create_histogram(self, worksheet, column_name):
        self.mtb.activate_worksheet(worksheet)
        command = f"""
Histogram '{column_name}';
Bar;
Distribution;
Normal.
"""
        logger.info("Histogram: {}", column_name)
        self.mtb.execute(command)

    def create_temperature_scatter(self, worksheet, metric):
        self.mtb.activate_worksheet(worksheet)
        command = f"""
Plot '{metric}'*'{X_TEMPERATURE}';
Symbol '{SERIES_COLUMN}';
Connect '{SERIES_COLUMN}'.
"""
        logger.info("Scatter: {} vs {}", metric, X_TEMPERATURE)
        self.mtb.execute(command)

    def distribution_identification(self, worksheet, column_name):
        self.mtb.activate_worksheet(worksheet)
        command = f"""DCapa '{column_name}' 9999;
All;
BoxCox;
Johnson 0.10;
RDescriptive;
RFitTests;
REstimate."""
        logger.info("Distribution ID: {}", column_name)
        self.mtb.execute(command)

    def create_cpk_analysis(self, worksheet, column_name, usl=3.0, lsl=None):
        self.mtb.activate_worksheet(worksheet)
        spec_lines = []
        if usl is not None and not _is_nan(usl):
            spec_lines.append(f"Uspec {usl};")
        if lsl is not None and not _is_nan(lsl):
            spec_lines.append(f"Lspec {lsl};")
        if not spec_lines:
            spec_lines.append("Uspec 3;")  # sensible fallback
        specs = "\n".join(spec_lines)
        command = f"""
Capa '{column_name}' 9999;
{specs}
Pooled;
AMR;
UnBiased;
OBiased;
Toler 6;
Within;
Overall;
NoCI;
PPM;
CStat.
"""
        logger.info("Cpk: {} (USL={}, LSL={})", column_name, usl, lsl)
        self.mtb.execute(command)

    def export_graph(self, path):
        self.mtb.execute(f'SAVE "{path}".')


def _is_nan(value) -> bool:
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False
