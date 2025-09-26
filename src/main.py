import os, sys

# Make sure the package is importable when running from source AND when frozen.
def _ensure_path():
    # When running from source repo, this puts src/ on sys.path
    here = os.path.abspath(os.path.dirname(__file__))
    parent = os.path.dirname(here)
    if parent not in sys.path:
        sys.path.insert(0, parent)
_ensure_path()

try:
    # Normal import path (included in the EXE)
    from openrecover.gui_qt import main
except Exception:
    # Fallback if someone runs the single file directly inside src/
    sys.path.append(os.path.join(os.path.dirname(__file__), "openrecover"))
    from gui_qt import main

if __name__ == "__main__":
    main()
