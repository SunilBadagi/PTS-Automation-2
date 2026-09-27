"""Central configuration for the PTS Automation app.

Every path is derived from the project root so the app is portable and does not
depend on the current working directory or any one machine's folder layout.
"""

from pathlib import Path
import sys

# Keep user data beside the executable when frozen; use the repository root in development.
BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
GRAPHS_DIR = OUTPUT_DIR / "graphs"

# Default input files (used only as pre-filled suggestions in the UI).
PTS_ANALYZER = INPUT_DIR / "PTS_Dev.xlsm"
RAW_DATA = INPUT_DIR / "rel2_1_bar_test.csv"

# Pipeline output workbook. It contains Processed Input, Data, and Stacked Data.
REPORT_OUTPUT = OUTPUT_DIR / "PTS_report.xlsx"
PROCESSED_INPUT = REPORT_OUTPUT
DATA_OUTPUT = REPORT_OUTPUT
STACKED_OUTPUT = REPORT_OUTPUT
PROJECT_FILE = OUTPUT_DIR / "Minitab_Project.mpx"
DISTRIBUTION_RTF = OUTPUT_DIR / "distribution.rtf"


def ensure_directories() -> None:
    """Create every output directory the pipeline writes to.

    Safe to call repeatedly; never raises if the folders already exist.
    """
    for directory in (OUTPUT_DIR, GRAPHS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


# Create output folders on import so downstream writes never fail on a missing dir.
ensure_directories()
