# OpenRecover – NTFS File Recovery Toolkit

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)
![GUI](https://img.shields.io/badge/gui-PySide6-orange.svg)

OpenRecover is a **Python-based file recovery toolkit** with a modern **PySide6 (Qt for Python) GUI**, targeting **NTFS partition recovery on Windows**.  
It is designed to be modular, testable, and user-friendly, enabling the recovery of deleted or lost files from NTFS volumes.

---

## ✨ Features

- **NTFS Partition Scanner**  
  Detects and enumerates deleted file entries directly from NTFS structures.

- **Parser & Recovery Engine**  
  Parses MFT (Master File Table) records and reconstructs files from raw disk data.

- **Modern GUI (PySide6 Widgets)**  
  Intuitive Windows-native interface for selecting drives, scanning, and recovering files.

- **Progress Tracking & Error Handling**  
  Background threads keep the UI responsive, with progress bars and clear error messages.

- **Modular Architecture**  
  Decoupled scanner, parser, recovery engine, and GUI for easy maintenance and testing.

---

## 📂 Project Structure

OpenRecover/
├── src/
│ ├── main.py # GUI entry point
│ ├── openrecover/
│ │ ├── gui.py # PySide6 Widgets GUI
│ │ ├── scanner.py # NTFS scanning logic
│ │ ├── parser.py # NTFS structure parsing
│ │ ├── recovery.py # File recovery engine
│ │ └── utils.py # Shared helpers, logging, error handling
├── installer/ # Inno Setup scripts for Windows installer
├── requirements.txt # Python dependencies
└── README.md # Project documentation


---

## 🚀 Getting Started

### Prerequisites
- Windows 10/11 with Administrator privileges  
- Python 3.11+  
- [PySide6](https://pypi.org/project/PySide6/) and dependencies  

Install dependencies:
```bash
pip install -r requirements.txt

Running from Source
python src/main.py

Building Executable

We use PyInstaller + Inno Setup for packaging:

pyinstaller -F -w -n OpenRecover src/main.py


The installer script is in installer/OpenRecoverProQt.iss.

🧪 Testing

Each module is independently testable:

scanner → Verify detection of deleted entries on test NTFS images

parser → Unit test MFT parsing with known byte sequences

recovery → Validate recovery on known-deleted test files

gui → Manual testing with PySide6 Widgets; automated smoke tests coming soon

Run all tests with:

pytest

📖 Roadmap

 Add QAbstractListModel for recovered file listing

 Implement session saving/resume functionality

 Add preview support for images/videos before recovery

 Improve error logging with structured log files

🤝 Contributing

Pull requests are welcome! Please follow the contribution guidelines
 and adhere to the project’s coding standards.

📜 License

This project is licensed under the MIT License. See LICENSE
 for details.

🔍 Keywords

NTFS Recovery · File Recovery · Data Carving · Disk Scanner · PySide6 GUI · Windows · Forensics · OpenRecover


---
