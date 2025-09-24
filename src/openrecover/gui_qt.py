import sys, os, time, threading
from PySide6 import QtCore, QtGui, QtWidgets

# Stylesheet
QSS = """
* { font-family: 'Segoe UI','Inter','Roboto'; font-size: 10.5pt; }
QMainWindow { background: #0F1115; }
QWidget { color: #E6E9EF; background: #0F1115; }
QFrame#Card { background: #171A21; border: 1px solid #232733; border-radius: 14px; }
QPushButton { background: #232733; border: 1px solid #2F3542; border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { background: #2A3140; }
QPushButton#Primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3B82F6, stop:1 #22D3EE); border: none; color: white; font-weight: 600; }
QLineEdit { background: #0B0D11; border: 1px solid #2A3040; border-radius: 8px; padding: 6px 8px; }
QProgressBar { border: 1px solid #2A3040; border-radius: 10px; background: #0B0D11; text-align: center; color: #AAB1BD; }
QProgressBar::chunk { border-radius: 10px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #22D3EE, stop:1 #3B82F6); }
QHeaderView::section { background: #171A21; border: 1px solid #232733; padding: 6px; }
QTableWidget { gridline-color: #232733; selection-background-color: #3B82F6; }
"""

APP = "OpenRecover Pro v0.7 (Qt)"

# Simple preview helper
def show_preview(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg",".jpeg",".png",".heic",".heif"):
        pix = QtGui.QPixmap(path)
        if pix.isNull():
            QtWidgets.QMessageBox.warning(None,"Preview","Cannot preview image")
            return
        lab = QtWidgets.QLabel()
        lab.setPixmap(pix.scaled(480,360, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        dlg = QtWidgets.QDialog()
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addWidget(lab)
        dlg.setWindowTitle("Preview")
        dlg.exec()
    else:
        if os.name=="nt":
            os.startfile(path)
        else:
            QtWidgets.QMessageBox.information(None,"Preview","No inline preview available")

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setMinimumSize(1120,740)
        self._ui()

    def _ui(self):
        cw = QtWidgets.QWidget()
        self.setCentralWidget(cw)
        root = QtWidgets.QVBoxLayout(cw)

        # Simple label just to verify GUI launches
        label = QtWidgets.QLabel("OpenRecover Pro GUI Ready")
        label.setAlignment(QtCore.Qt.AlignCenter)
        root.addWidget(label)

        # Table (results)
        self.table = QtWidgets.QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(["type","start","length","path","ok","note"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        # Add right-click preview menu
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._ctx_menu)

    def _ctx_menu(self,pos):
        menu = QtWidgets.QMenu(self)
        act = menu.addAction("Preview")
        act.triggered.connect(self._preview_selected)
        menu.exec(self.table.mapToGlobal(pos))

    def _preview_selected(self):
        row=self.table.currentRow()
        if row>=0:
            path=self.table.item(row,3).text() if self.table.item(row,3) else None
            if path and os.path.exists(path):
                show_preview(path)

# --- Entry point ---
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = Main()
    w.show()
    sys.exit(app.exec())
