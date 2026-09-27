"""Application launcher.

    python run.py            # launch the GUI (default)
    python run.py --headless # run the pipeline once with defaults, no GUI
"""

import sys


def main():
    if "--headless" in sys.argv:
        from app.main import run
        run()
    else:
        from ui.app import main as run_gui
        run_gui()


if __name__ == "__main__":
    main()
