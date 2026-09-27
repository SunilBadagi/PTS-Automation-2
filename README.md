# PTS Automation

Takes a raw chamber **CSV**, drives the **PTS analyzer** VBA macros in Excel to
produce the `Data` and `Stacked Data` sheets, then pushes those into **Minitab**
to generate the configured graphs.

## Run

```bash
pip install -r requirements.txt
python run.py              # launch the GUI
python run.py --headless   # run once with defaults, no GUI
```

## Build a Windows executable

On Windows PowerShell, run:

```powershell
.\build_exe.ps1
```

The executable is created at `dist/PTS-Automation.exe`. Keep the generated
`input`, `output`, and `logs` folders beside it. Excel is required for the PTS
macro stage, and Minitab is required for Minitab graph generation.

## Pipeline

```
CSV ──► preprocess ──► Excel/VBA macros ──► extract sheets ──► Minitab graphs
```

The whole run happens on a **background thread** (`ui/worker.py`), so the window
never freezes. Progress and a live log stream to the UI, and the run can be
cancelled between stages.

The pipeline writes one workbook, `output/PTS_report.xlsx`, containing the
`Processed Input`, `Data`, and `Stacked Data` worksheets.

In the UI's **ASIC Conversion** section, select `ASIC 3224` to convert raw
pressure counts using `counts / 2^24 * 100`. `ELMOS` uses the existing
conversion and is selected by default.

## Structure

| Area | Path | Responsibility |
|------|------|----------------|
| Settings | `app/config/settings.py` | All paths, derived from the project root |
| Models | `app/models/` | `PTSConfig`, `GraphConfig`, `PipelineConfig` (validated) |
| Services | `app/services/` | preprocess, Excel runner, extractor, orchestrator |
| Minitab | `minitab/app/` | Minitab COM service + graph builders |
| UI | `ui/` | PyQt5 window, config tab, worker thread, theme |

## Robustness notes

- **Excel COM** is wrapped in a context manager (`PTSRunner`) that always quits
  Excel, even on error — no orphaned `EXCEL.EXE` processes.
- **Minitab absent** (e.g. dev machines) is handled gracefully: graphing is
  skipped with a warning and the Excel outputs are still produced.
- **CSV parsing** tolerates both known layouts (with/without a part-number
  banner line) and the duplicated pressure column.
- **Paths** never depend on the current working directory.
- The embedded Excel/Minitab **ActiveX views load lazily** and are guarded, so
  the app launches even where those apps aren't registered.

## Graph configuration (in the UI)

The Configuration tab exposes: which graphs to generate (scatter / histogram /
distribution ID / Cpk), the metric columns per graph, the TEB temperature
buckets, and the Cpk USL/LSL spec limits.
