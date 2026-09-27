"""Application launcher.

    python run.py            # launch the GUI (default)
    python run.py --headless # run the pipeline once with defaults, no GUI
    python run.py --headless run1.csv run2.xlsx ...  # analyse + merge these runs
"""

import sys


def main():
    if "--headless" in sys.argv:
        from app.main import run
        files = [a for a in sys.argv[1:] if a != "--headless"]
        run(files)
    else:
        from ui.app import main as run_gui
        run_gui()


if __name__ == "__main__":
    main()
