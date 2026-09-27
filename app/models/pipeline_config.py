"""A single object that carries everything the pipeline needs to run.

Bundling paths + configs here means no stage depends on the current working
directory or on module-level globals, which was a source of crashes before.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.models.graph_config import GraphConfig
from app.models.pts_config import ConfigError, PTSConfig


@dataclass
class PipelineConfig:
    pts: PTSConfig
    graph: GraphConfig = field(default_factory=GraphConfig)

    # Inputs. ``raw_data_files`` holds every char-run (batch) file; when it is
    # empty the single ``raw_data`` file is used.
    raw_data: Path = field(default_factory=lambda: Path(settings.RAW_DATA))
    raw_data_files: List[Path] = field(default_factory=list)
    pts_analyzer: Path = field(default_factory=lambda: Path(settings.PTS_ANALYZER))

    # Outputs
    processed_input: Path = field(
        default_factory=lambda: Path(settings.PROCESSED_INPUT)
    )
    data_output: Path = field(default_factory=lambda: Path(settings.DATA_OUTPUT))
    stacked_output: Path = field(
        default_factory=lambda: Path(settings.STACKED_OUTPUT)
    )
    project_file: Path = field(default_factory=lambda: Path(settings.PROJECT_FILE))
    distribution_rtf: Path = field(
        default_factory=lambda: Path(settings.DISTRIBUTION_RTF)
    )
    # Per-run workbooks (Processed Input + Data + Stacked Data for one batch).
    # Defaults to a "runs" folder beside the master report.
    runs_dir: Optional[Path] = None

    # Behaviour flags
    run_minitab: bool = True
    keep_excel_open: bool = False

    def __post_init__(self):
        # Normalise every path field to a Path object.
        for name in (
            "raw_data",
            "pts_analyzer",
            "processed_input",
            "data_output",
            "stacked_output",
            "project_file",
            "distribution_rtf",
            "runs_dir",
        ):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, Path(value))
        self.raw_data_files = [Path(p) for p in self.raw_data_files]
        if self.runs_dir is None:
            self.runs_dir = self.data_output.parent / settings.RUNS_DIR.name

    @property
    def input_files(self) -> List[Path]:
        """Every char file to analyse, in run order."""
        return list(self.raw_data_files) or [self.raw_data]

    def validate(self) -> None:
        """Validate configs and that required input files exist."""
        self.pts.validate()
        self.graph.validate()

        files = self.input_files
        missing = [str(p) for p in files if not p.exists()]
        if missing:
            raise ConfigError("Char data file(s) not found:\n" + "\n".join(missing))
        if not self.pts_analyzer.exists():
            raise ConfigError(
                f"PTS analyzer workbook not found:\n{self.pts_analyzer}"
            )

        # Make sure output directories exist.
        for out in (
            self.processed_input,
            self.data_output,
            self.stacked_output,
            self.project_file,
            self.distribution_rtf,
        ):
            out.parent.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
