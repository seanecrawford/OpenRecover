# OpenRecover package marker
__version__ = "0.7.0"

# Don't import submodules here.
# PyInstaller loads packages a bit differently; importing gui_qt/rawio/etc
# at package import time can cause "module not found" during boot.
