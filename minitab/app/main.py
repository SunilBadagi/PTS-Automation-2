"""Minitab graphing stage, driven by a PipelineConfig.

Reads the extracted Data / Stacked Data sheets, computes the TEB range column,
pushes both worksheets into Minitab and generates the graphs the user enabled.
"""

import pythoncom  # pyright: ignore[reportMissingImports]

from app.models.graph_config import GraphConfig
from app.utils.logger import logger
from minitab.app.services.data_loader import DataLoader
from minitab.app.services.graph_service import GraphService
from minitab.app.services.minitab_service import MinitabService, MinitabUnavailable
from minitab.app.services.teb_range_service import TEBRangeService

STACKED_WS = "Stacked Data"
DATA_WS = "Data Analysis"


def run_minitab(config, progress=None, log=None):
    """Run the Minitab graphing stage.

    ``config`` is a PipelineConfig. ``progress(pct, msg)`` and ``log(msg)`` are
    optional callbacks. Raises MinitabUnavailable if Minitab isn't installed.
    """
    progress = progress or (lambda pct, msg: None)
    log = log or (lambda msg: None)
    graph_cfg: GraphConfig = getattr(config, "graph", None) or GraphConfig()

    def emit(pct, msg):
        logger.info(msg)
        log(msg)
        progress(pct, msg)

    # COM must be initialised on the calling (possibly background) thread.
    pythoncom.CoInitialize()
    try:
        emit(80, "Loading extracted data")
        stacked_df = DataLoader.load_stacked_data(config.stacked_output)
        data_df = DataLoader.load_data(config.data_output)

        # The pipeline computes the TEB range columns before this step runs. If
        # run standalone on a data sheet that lacks them, compute them here too.
        changed = False
        for r in graph_cfg.teb_ranges:
            if r.name not in data_df.columns:
                data_df = TEBRangeService.calculate_range(
                    data_df, r.temps, r.name
                )
                changed = True
        if changed:
            import pandas as pd

            with pd.ExcelWriter(
                config.data_output,
                engine="openpyxl",
                mode="a",
                if_sheet_exists="replace",
            ) as writer:
                data_df.to_excel(writer, sheet_name="Data", index=False)

        emit(83, "Connecting to Minitab")
        mtb = MinitabService()  # raises MinitabUnavailable if not installed

        stacked_ws = mtb.create_worksheet(STACKED_WS)
        mtb.load_dataframe(stacked_df, stacked_ws)

        data_ws = mtb.create_worksheet(DATA_WS)
        mtb.load_dataframe(data_df, data_ws)

        graphs = GraphService(mtb)

        if graph_cfg.enable_scatter:
            emit(86, "Building scatter plots")
            for metric in graph_cfg.scatter_metrics:
                graphs.create_temperature_scatter(STACKED_WS, metric)

        if graph_cfg.enable_histogram:
            emit(89, "Building histograms")
            for metric in graph_cfg.histogram_metrics:
                graphs.create_histogram(DATA_WS, metric)

        cpk_metrics = graph_cfg.cpk_metrics or [graph_cfg.cpk_column]
        cpk_usls = graph_cfg.cpk_usls or {}
        if graph_cfg.enable_distribution_id:
            emit(92, "Distribution identification")
            for metric in cpk_metrics:
                graphs.distribution_identification(DATA_WS, metric)
            mtb.save_command_output(config.distribution_rtf)

        if graph_cfg.enable_cpk:
            emit(95, "Cpk / capability analysis")
            for metric in cpk_metrics:
                graphs.create_cpk_analysis(
                    DATA_WS,
                    column_name=metric,
                    usl=cpk_usls.get(metric, graph_cfg.cpk_usl),
                    lsl=None,
                )

        emit(98, "Saving Minitab project")
        mtb.save_project(config.project_file)
        emit(99, "Minitab graphing complete")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    from app.main import build_default_config

    try:
        run_minitab(build_default_config())
    except MinitabUnavailable as exc:
        print(f"Minitab not available: {exc}")
