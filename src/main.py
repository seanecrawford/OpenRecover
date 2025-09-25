def main():
    # Lazy import so packaging and boot order are predictable for PyInstaller
    from openrecover.gui_qt import main as gui_main
    gui_main()

if __name__ == "__main__":
    main()
