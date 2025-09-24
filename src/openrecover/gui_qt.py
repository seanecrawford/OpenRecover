# … keep the rest of your imports …
from PySide6 import QtCore, QtGui, QtWidgets
import os, sys, threading, time

APP = "OpenRecover Pro v0.7 (Qt)"

# add preview helper
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
        # fallback → open externally
        if os.name=="nt":
            os.startfile(path)
        else:
            QtWidgets.QMessageBox.information(None,"Preview","No inline preview. Open manually.")

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setMinimumSize(1120,740)
        self._speed_state={"last_c":0,"last_t":time.monotonic()}
        self._ui()

    def _ui(self):
        # … all your existing UI code …
        self.table=QtWidgets.QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(["type","start","length","path","ok","note"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Add context menu for preview
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._ctx_menu)

        # … rest of layout …

    def _ctx_menu(self,pos):
        menu=QtWidgets.QMenu(self)
        act=menu.addAction("Preview")
        act.triggered.connect(self._preview_selected)
        menu.exec(self.table.mapToGlobal(pos))

    def _preview_selected(self):
        row=self.table.currentRow()
        if row>=0:
            path=self.table.item(row,3).text()
            if path and os.path.exists(path):
                show_preview(path)
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = Main()
    w.show()
    sys.exit(app.exec())
