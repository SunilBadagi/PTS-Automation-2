"""Headless entry point for running the pipeline without the GUI."""

from app.models.graph_config import GraphConfig
from app.models.pipeline_config import PipelineConfig
from app.models.pts_config import PTSConfig
from app.services.pipeline import Pipeline

DEFAULT_PTS = dict(
    pressure_min=0,
    pressure_max=1,
    output_min=10,
    output_max=90,
    supply_voltage=3.3,
    pressure_az=0,
    teb_limit=3,
    offset_limit=2,
    span_limit=2,
    linearity_limit=0.2,
    pressure_hyst=0.18,
    temp_hyst=1.1,
    accuracy=0.25,
    sensor_type="differential",
    pressure_unit="inH2O",
)


def build_default_config(raw_data=None, project_file=None, run_minitab=True,
                         raw_data_files=None):
    """Assemble a PipelineConfig from defaults, overriding a couple of paths."""
    pts = PTSConfig(**DEFAULT_PTS)
    config = PipelineConfig(pts=pts, graph=GraphConfig(), run_minitab=run_minitab)
    if raw_data is not None:
        config.raw_data = raw_data
    if raw_data_files:
        config.raw_data_files = list(raw_data_files)
    if project_file is not None:
        config.project_file = project_file
    config.__post_init__()  # re-normalise overridden paths
    return config


def run_pipeline(config=None, raw_data=None, project_file=None, run_minitab=True):
    """Run the whole pipeline and return a PipelineResult.

    Kept for backward compatibility with older callers. Prints progress to stdout.
    """
    if config is None or not isinstance(config, PipelineConfig):
        # Legacy signature: `config` may be a bare PTSConfig or None.
        pts = config if isinstance(config, PTSConfig) else PTSConfig(**DEFAULT_PTS)
        pipeline_config = PipelineConfig(
            pts=pts, graph=GraphConfig(), run_minitab=run_minitab
        )
        if raw_data is not None:
            pipeline_config.raw_data = raw_data
        if project_file is not None:
            pipeline_config.project_file = project_file
        pipeline_config.__post_init__()
    else:
        pipeline_config = config

    pipeline = Pipeline(
        progress=lambda pct, msg: print(f"[{pct:3d}%] {msg}"),
        log=lambda msg: None,
    )
    result = pipeline.run(pipeline_config)
    print(result.message)
    return result


def run(raw_data_files=None):
    """Run once with defaults; ``raw_data_files`` are the char run files to merge."""
    if raw_data_files:
        return run_pipeline(build_default_config(raw_data_files=raw_data_files))
    return run_pipeline()


if __name__ == "__main__":
    run()
