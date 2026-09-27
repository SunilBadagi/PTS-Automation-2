"""A single object that carries everything the pipeline needs to run.

Bundling paths + configs here means no stage depends on the current working
directory or on module-level globals, which was a source of crashes before.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.graph_config import GraphConfig
from app.models.pts_config import ConfigError, PTSConfig


@dataclass
class PipelineConfig:
    pts: PTSConfig
    graph: GraphConfig = field(default_factory=GraphConfig)

    # Inputs
    raw_data: Path = field(default_factory=lambda: Path(settings.RAW_DATA))
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
        ):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, Path(value))

    def validate(self) -> None:
        """Validate configs and that required input files exist."""
        self.pts.validate()
        self.graph.validate()

        if not self.raw_data.exists():
            raise ConfigError(f"CSV file not found:\n{self.raw_data}")
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
