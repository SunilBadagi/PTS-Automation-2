# PTS Automation

Takes one or more raw chamber **char run files** (CSV or Excel), drives the
**PTS analyzer** VBA macros in Excel on each one to produce its `Data` and
`Stacked Data` sheets, merges every run into one master data set, then pushes
that into **Minitab** to generate the configured graphs.

Char is run in batches (e.g. 30 or 60 sensors per chamber run) because of
hardware limits, so a 100-200 sensor population arrives as several run files.
Add them all in the UI and they are analysed one by one and stacked together.

## Run

```bash
pip install -r requirements.txt
python run.py              # launch the GUI
python run.py --headless   # run once with defaults, no GUI
python run.py --headless "Run 1.csv" "Run 2.xlsx"   # analyse + merge these runs
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
for each run file:  preprocess ──► Excel/VBA macros ──► extract sheets
then:               merge runs ──► TEB range columns ──► Minitab graphs
```

The whole run happens on a **background thread** (`ui/worker.py`), so the window
never freezes. Progress and a live log stream to the UI, and the run can be
cancelled between stages.

Outputs:

- `output/runs/NN_<run file>.xlsx`: one workbook per run with its
  `Processed Input`, `Data`, and `Stacked Data` sheets.
- `output/PTS_report.xlsx`: the master workbook, with `Data` and
  `Stacked Data` merged across all runs (a `Char Run` column says which run
  each row came from) plus a `Run Summary` sheet. Minitab uses this workbook.

If one run file fails, the rest are still merged and the failure is reported.
A warning is logged if a serial number appears in more than one run.

Char file layout: row 1 = sensor / part name, row 2 = column headings,
data from row 3. Files whose header is already on row 1 are also accepted.

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
- **Char file parsing** (CSV or Excel) tolerates both known layouts (with/without a part-number
  banner line) and the duplicated pressure column.
- **Paths** never depend on the current working directory.
- The embedded Excel/Minitab **ActiveX views load lazily** and are guarded, so
  the app launches even where those apps aren't registered.

## Graph configuration (in the UI)

The Configuration tab exposes: which graphs to generate (scatter / histogram /
distribution ID / Cpk), the metric columns per graph, the TEB temperature
buckets, and the Cpk USL/LSL spec limits.
