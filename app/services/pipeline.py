"""End-to-end pipeline orchestrator.

Runs the stages in order and reports progress through simple callbacks so it can
be driven from a background thread without freezing the UI:

    for each char run (batch) file:
        preprocess -> Excel/VBA macros -> extract sheets   (one workbook per run)
    merge runs -> TEB range columns -> Minitab graphs      (master workbook)

The orchestrator is deliberately UI-agnostic (no PyQt imports) and never raises
past ``run()``: it returns a PipelineResult describing success/failure.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import pandas as pd

from app.models.pipeline_config import PipelineConfig
from app.services.excel_preprocessor import ExcelPreprocessor
from app.services.pts_extractor import PTSExtractor
from app.services.pts_runner import PTSRunner
from app.services.run_merger import RunMerger, RunOutput
from app.utils.logger import logger

ProgressCb = Callable[[int, str], None]
LogCb = Callable[[str], None]
CancelCb = Callable[[], bool]


class PipelineCancelled(RuntimeError):
    """Raised internally when the user cancels between stages."""


@dataclass
class PipelineResult:
    success: bool
    message: str
    warnings: List[str] = field(default_factory=list)


class Pipeline:
    def __init__(
        self,
        progress: Optional[ProgressCb] = None,
        log: Optional[LogCb] = None,
        is_cancelled: Optional[CancelCb] = None,
    ):
        self._progress = progress or (lambda pct, msg: None)
        self._log = log or (lambda msg: None)
        self._is_cancelled = is_cancelled or (lambda: False)
        self.warnings: List[str] = []

    # -- helpers ---------------------------------------------------------
    def _emit(self, pct: int, msg: str):
        logger.info(msg)
        self._log(msg)
        self._progress(pct, msg)

    def _checkpoint(self):
        if self._is_cancelled():
            raise PipelineCancelled()

    def _warn(self, msg: str):
        logger.warning(msg)
        self.warnings.append(msg)
        self._log(f"WARNING: {msg}")

    # -- entry point -----------------------------------------------------
    def run(self, config: PipelineConfig) -> PipelineResult:
        try:
            config.validate()
        except Exception as exc:  # ConfigError and friends
            return PipelineResult(False, str(exc))

        try:
            self._emit(2, "Starting pipeline")
            self._checkpoint()

            runs, failed = self._analyse_runs(config)
            self._checkpoint()

            self._merge(config, runs)
            self._checkpoint()

            self._compute_derived(config)
            self._checkpoint()

            if config.run_minitab:
                self._run_minitab(config)
            else:
                self._emit(90, "Minitab step disabled; skipping.")

            self._emit(100, "Pipeline finished")
            msg = f"Pipeline completed: {len(runs)} run(s) merged."
            if failed:
                msg += f" {len(failed)} run(s) FAILED: {', '.join(failed)}."
            if self.warnings:
                msg += f" ({len(self.warnings)} warning(s) -- see log.)"
            return PipelineResult(True, msg, self.warnings)

        except PipelineCancelled:
            self._log("Pipeline cancelled by user.")
            return PipelineResult(False, "Cancelled by user.", self.warnings)
        except Exception as exc:  # noqa: BLE001 - surface any stage failure
            logger.exception("Pipeline failed")
            self._log(f"ERROR: {exc}")
            return PipelineResult(False, str(exc), self.warnings)

    # -- stages ----------------------------------------------------------
    # Per-run work spans RUNS_START..RUNS_END percent of the progress bar.
    RUNS_START, RUNS_END = 3, 72

    def _analyse_runs(self, config: PipelineConfig):
        """Run every char file through the analyzer; one workbook per run.

        A failed run is recorded as a warning and the batch carries on, so one
        bad file doesn't throw away the others. Fails only if every run fails.
        """
        files = config.input_files
        total = len(files)
        span = (self.RUNS_END - self.RUNS_START) / total
        runs, failed = [], []

        for index, source in enumerate(files):
            self._checkpoint()
            label = source.stem
            workbook = config.runs_dir / f"{index + 1:02d}_{_safe_name(label)}.xlsx"
            base = self.RUNS_START + index * span

            def pct(fraction, base=base):
                return int(base + fraction * span)

            self._emit(pct(0), f"Run {index + 1}/{total}: {source.name}")
            try:
                self._preprocess(config, source, workbook, pct)
                self._checkpoint()
                self._run_excel(config, workbook, pct)
                self._checkpoint()
                self._extract(config, workbook, pct)
            except PipelineCancelled:
                raise
            except Exception as exc:  # noqa: BLE001 - keep going with other runs
                logger.exception("Run failed: {}", source)
                self._warn(f"Run {index + 1} ('{source.name}') failed: {exc}")
                failed.append(source.name)
                continue
            runs.append(RunOutput(label=label, source=source, workbook=workbook))

        if not runs:
            raise RuntimeError(
                f"All {total} run(s) failed; nothing to merge. See the log."
            )
        return runs, failed

    def _preprocess(self, config: PipelineConfig, source, workbook, pct):
        self._emit(pct(0.05), "  Preprocessing char data")
        ExcelPreprocessor().process(source, workbook, config.pts.asic_type)

    def _run_excel(self, config: PipelineConfig, workbook, pct):
        self._emit(pct(0.15), "  Opening PTS analyzer in Excel")
        with PTSRunner(
            config.pts_analyzer,
            visible=True,
            keep_open=config.keep_excel_open,
        ) as pts:
            self._emit(pct(0.25), "  Applying transfer-function inputs")
            pts.set_transfer_function_inputs(config.pts)
            pts.set_product_spec_inputs(config.pts)
            pts.set_raw_data_path(workbook)
            self._checkpoint()

            self._emit(pct(0.35), "  Running macro: ImportDataAccFile_Auto")
            pts.run_macro("ImportDataAccFile_Auto")
            self._checkpoint()

            self._emit(pct(0.6), "  Running macro: AllTempAnalysis")
            pts.run_macro("AllTempAnalysis")

            self._emit(pct(0.85), "  Saving workbook")
            pts.save()

    def _extract(self, config: PipelineConfig, workbook, pct):
        self._emit(pct(0.92), "  Extracting Data and Stacked Data sheets")
        PTSExtractor().extract(config.pts_analyzer, workbook, workbook)

    def _merge(self, config: PipelineConfig, runs):
        self._emit(73, f"Merging {len(runs)} run(s) into master Data / Stacked Data")
        for msg in RunMerger().merge(runs, config.data_output):
            self._warn(msg)
        self._log(f"Master workbook: {config.data_output}")

    def _compute_derived(self, config: PipelineConfig):
        """Add TEB range columns to the Data sheet in the report workbook.

        This is a pure-pandas data transform (no COM), so it always runs after
        extraction -- independent of whether the Minitab graphing step runs.
        Without this, the TEB @(0-50) column would only be filled when Minitab
        was enabled.
        """
        # These imports are pure pandas and safe even where Minitab is absent.
        from minitab.app.services.data_loader import DataLoader
        from minitab.app.services.teb_range_service import TEBRangeService

        ranges = config.graph.teb_ranges
        self._emit(76, f"Computing {len(ranges)} TEB range column(s)")
        data_df = DataLoader.load_data(config.data_output)
        for r in ranges:
            data_df = TEBRangeService.calculate_range(data_df, r.temps, r.name)
            filled = int(data_df[r.name].notna().sum())
            self._log(f"'{r.name}': {filled}/{len(data_df)} rows populated.")

        try:
            with pd.ExcelWriter(
                config.data_output,
                engine="openpyxl",
                mode="a",
                if_sheet_exists="replace",
            ) as writer:
                data_df.to_excel(writer, sheet_name="Data", index=False)
        except PermissionError as exc:
            raise RuntimeError(
                f"Cannot write '{config.data_output}'. Is it open in Excel? ({exc})"
            ) from exc

    def _run_minitab(self, config: PipelineConfig):
        self._emit(80, "Preparing Minitab graphs")
        # Imported lazily so the whole app doesn't require Minitab to be present.
        from minitab.app.main import run_minitab

        try:
            run_minitab(
                config,
                progress=lambda pct, msg: self._progress(pct, msg),
                log=self._log,
            )
        except MinitabUnavailable as exc:
            self._warn(
                f"Minitab is not available on this machine; graphing skipped. ({exc})"
            )
        except Exception as exc:  # noqa: BLE001
            # A graphing failure should not throw away the Excel results already
            # produced; record it as a warning instead.
            self._warn(f"Minitab graphing failed: {exc}")


def _safe_name(name: str) -> str:
    """Make a file-system-safe, reasonably short name from a run label."""
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .")
    return cleaned[:80] or "run"


# Re-exported here so callers can catch it without importing the minitab package.
try:
    from minitab.app.services.minitab_service import MinitabUnavailable
except Exception:  # pragma: no cover - fallback if package layout changes
    class MinitabUnavailable(RuntimeError):
        pass
