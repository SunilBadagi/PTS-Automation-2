"""Configuration for the Minitab graphing stage.

These dataclasses let the UI decide *which* graphs to generate, *which* columns
each one plots, the TEB range columns (each its own name + temperature set), and
the Cpk spec limits -- instead of those choices being hard-coded.
"""

from dataclasses import dataclass, field
from typing import List

# Column names as they appear in the extracted "Stacked Data" / "Data" sheets.
X_TEMPERATURE = "Temperature (Deg C)"
SERIES_COLUMN = "Serial Number"

DEFAULT_SCATTER_METRICS = [
    "TEB (%FSS)",
    "Offset Error (%FSS)",
    "Span Error (%FSS)",
]
DEFAULT_HISTOGRAM_METRICS = [
    "TEB @(0-50)",
    "Accuracy Error",
]
CPK_METRICS = [
    "TEB @(0-50)",
    "TEB @(-20 - 85)",
    "TEB @(-40 - 110)",
    "Accuracy Error",
]


@dataclass
class TEBRange:
    """One TEB range column: its name and the temperatures it spans.

    The value written is max(|TEB @ t|) over ``temps``.
    """
    name: str
    temps: List[float] = field(default_factory=list)


def _default_teb_ranges() -> List[TEBRange]:
    return [
        TEBRange("TEB @(0-50)", [0, 10, 25, 50]),
        TEBRange("TEB @(-20 - 85)", [-20, 0, 10, 25, 50, 85]),
        TEBRange("TEB @(-40 - 110)", [-40, -20, 0, 10, 25, 50, 85, 110]),
    ]


DEFAULT_TEB_RANGES = _default_teb_ranges()


@dataclass
class GraphConfig:
    """User-configurable graphing options."""

    # Which graph types to generate.
    enable_scatter: bool = True
    enable_histogram: bool = True
    enable_distribution_id: bool = True
    enable_cpk: bool = True

    # Columns/metrics per graph type.
    scatter_metrics: List[str] = field(
        default_factory=lambda: list(DEFAULT_SCATTER_METRICS)
    )
    histogram_metrics: List[str] = field(
        default_factory=lambda: list(DEFAULT_HISTOGRAM_METRICS)
    )

    # One or more TEB range columns to compute onto the Data sheet.
    teb_ranges: List[TEBRange] = field(default_factory=_default_teb_ranges)

    # Column and spec limits used by the distribution ID + Cpk analyses.
    cpk_column: str = "TEB @(0-50)"
    cpk_usl: float = 3.0
    cpk_lsl: float = float("nan")  # NaN => one-sided (upper spec only)
    cpk_metrics: List[str] = field(default_factory=list)
    cpk_usls: dict = field(default_factory=dict)

    def validate(self) -> None:
        from app.models.pts_config import ConfigError

        if not self.teb_ranges:
            raise ConfigError("At least one TEB range column is required.")
        seen = set()
        for r in self.teb_ranges:
            if not r.name.strip():
                raise ConfigError("A TEB range column has an empty name.")
            if r.name in seen:
                raise ConfigError(f"Duplicate TEB range column name: '{r.name}'.")
            seen.add(r.name)
            if not r.temps:
                raise ConfigError(
                    f"TEB range '{r.name}' has no temperatures."
                )
        if self.enable_scatter and not self.scatter_metrics:
            raise ConfigError(
                "Scatter plots are enabled but no metrics were selected."
            )
        if self.enable_histogram and not self.histogram_metrics:
            raise ConfigError(
                "Histograms are enabled but no metrics were selected."
            )
        if self.enable_cpk and not (self.cpk_metrics or self.cpk_column.strip()):
            raise ConfigError("Cpk is enabled but no metrics were selected.")


# -- text <-> teb_ranges helpers (used by the UI) ------------------------

def _fmt_temp(t) -> str:
    f = float(t)
    return str(int(f)) if f.is_integer() else str(f)


def format_teb_ranges(ranges: List[TEBRange]) -> str:
    """Render ranges as editable text, one per line: ``Name = t1, t2, ...``."""
    return "\n".join(
        f"{r.name} = {', '.join(_fmt_temp(t) for t in r.temps)}"
        for r in ranges
    )


def parse_teb_ranges(text: str) -> List[TEBRange]:
    """Parse the multi-line ``Name = t1, t2, ...`` editor into TEBRange objects."""
    ranges: List[TEBRange] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(
                f"Line {lineno}: expected 'Name = t1, t2, ...'  (got '{line}')."
            )
        name, temps_str = line.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Line {lineno}: missing column name.")
        temps: List[float] = []
        for tok in temps_str.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                temps.append(float(tok))
            except ValueError:
                raise ValueError(
                    f"Line {lineno} ('{name}'): '{tok}' is not a number."
                )
        if not temps:
            raise ValueError(f"Line {lineno} ('{name}'): no temperatures given.")
        ranges.append(TEBRange(name, temps))
    if not ranges:
        raise ValueError("At least one TEB range column is required.")
    return ranges
