import sys
import multiprocessing

def _run():
    # Import inside the function so PyInstaller can analyze it cleanly.
    from openrecover.gui_qt import main as gui_main
    return gui_main()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(_run())
