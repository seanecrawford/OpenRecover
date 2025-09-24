import sys, os, time, threading
from PySide6 import QtCore, QtGui, QtWidgets
from .carver import FileCarver
from .signatures import ALL_SIGNATURES
from .rawio import to_raw_if_drive

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

# Preview helper
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

class Worker(QtCore.QObject):
    progress = QtCore.Signal(object, object)
    hit      = QtCore.Signal(object)
    done     = QtCore.Signal()
    error    = QtCore.Signal(str)

    def __init__(self, src, out, opts):
        super().__init__()
        self.src, self.out, self.opts = src, out, opts

    @QtCore.Slot()
    def run(self):
        try:
            carver = FileCarver(
                self.src, self.out, ALL_SIGNATURES,
                chunk=self.opts["chunk"], overlap=self.opts["overlap"],
                max_files=self.opts["max_files"], fast_index=self.opts["fast_index"],
                max_bytes=self.opts["max_bytes"], min_size=self.opts["min_size"],
                progress_cb=lambda c,t: self.progress.emit(c,t),
                deduplicate=self.opts["dedup"]
            )
            carver.hit_cb = lambda r: self.hit.emit(r)
            carver.scan()
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setMinimumSize(1120,740)
        self._speed_state={"last_c":0,"last_t":time.monotonic()}
        self._ui()

    def _ui(self):
        cw = QtWidgets.QWidget(); self.setCentralWidget(cw)
        root = QtWidgets.QVBoxLayout(cw)

        # Branding header with Sprig logo + text
        header = QtWidgets.QHBoxLayout()
        logo = QtWidgets.QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "spriglogo.png")
        pix = QtGui.QPixmap(logo_path)
        if not pix.isNull():
            logo.setPixmap(pix.scaled(32,32, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        text = QtWidgets.QLabel("Sprig")
        text.setStyleSheet("color: #00FF7F; font-size: 18pt; font-weight: bold; margin-left: 8px;")
        header.addWidget(logo)
        header.addWidget(text)
        header.addStretch()
        root.addLayout(header)

        # Top panel: source + output
        top = QtWidgets.QFrame(objectName="Card")
        g = QtWidgets.QGridLayout(top)
        self.edSrc=QtWidgets.QLineEdit(); self.edOut=QtWidgets.QLineEdit()
        bFile=QtWidgets.QPushButton("File..."); bDrive=QtWidgets.QPushButton("Drive..."); bOut=QtWidgets.QPushButton("Browse")
        bFile.clicked.connect(self.pick_file); bDrive.clicked.connect(self.pick_drive); bOut.clicked.connect(self.pick_out)
        g.addWidget(QtWidgets.QLabel("Source"),0,0); g.addWidget(self.edSrc,0,1,1,3); g.addWidget(bFile,0,4); g.addWidget(bDrive,0,5)
        g.addWidget(QtWidgets.QLabel("Output"),1,0); g.addWidget(self.edOut,1,1,1,3); g.addWidget(bOut,1,4,1,2)
        root.addWidget(top)

        # Options
        ops=QtWidgets.QFrame(objectName="Card"); og=QtWidgets.QGridLayout(ops)
        self.edChunk=QtWidgets.QLineEdit("16M"); self.edOv=QtWidgets.QLineEdit("256K")
        self.edMaxB=QtWidgets.QLineEdit("0"); self.edMin=QtWidgets.QLineEdit("256")
        self.spMax=QtWidgets.QSpinBox(); self.spMax.setRange(0,1000000)
        self.ckFast=QtWidgets.QCheckBox("Fast index"); self.ckAllow=QtWidgets.QCheckBox("Allow same-disk (unsafe)")
        self.ckDedup=QtWidgets.QCheckBox("Deduplicate"); self.ckDedup.setChecked(True)
        self.btnImage=QtWidgets.QPushButton("Create Image..."); self.btnScan=QtWidgets.QPushButton("Start Scan"); self.btnScan.setObjectName("Primary")
        self.btnScan.clicked.connect(self.start_scan)
        og.addWidget(QtWidgets.QLabel("Chunk"),0,0); og.addWidget(self.edChunk,0,1)
        og.addWidget(QtWidgets.QLabel("Overlap"),0,2); og.addWidget(self.edOv,0,3)
        og.addWidget(QtWidgets.QLabel("Max bytes"),0,4); og.addWidget(self.edMaxB,0,5)
        og.addWidget(QtWidgets.QLabel("Min size"),0,6); og.addWidget(self.edMin,0,7)
        og.addWidget(QtWidgets.QLabel("Max files"),0,8); og.addWidget(self.spMax,0,9)
        og.addWidget(self.ckFast,1,0,1,2); og.addWidget(self.ckAllow,1,2,1,3); og.addWidget(self.ckDedup,1,5,1,2)
        og.addWidget(self.btnImage,1,9); og.addWidget(self.btnScan,1,10)
        root.addWidget(ops)

        # Progress + table
        tbl=QtWidgets.QFrame(objectName="Card"); vg=QtWidgets.QVBoxLayout(tbl)
        self.pb=QtWidgets.QProgressBar(); self.pb.setMaximum(0); self.lbl=QtWidgets.QLabel("Idle")
        hh=QtWidgets.QHBoxLayout(); hh.addWidget(self.pb,1); hh.addWidget(self.lbl); vg.addLayout(hh)
        self.table=QtWidgets.QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(["type","start","length","path","ok","note"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._ctx_menu)
        vg.addWidget(self.table,1)
        root.addWidget(tbl,1)

    # Pickers
    def pick_file(self):
        p=QtWidgets.QFileDialog.getOpenFileName(self,"Choose IMAGE","","Images (*.img *.dd *.bin *.raw *.iso);;All files (*.*)")[0]
        if p: self.edSrc.setText(p)

    def pick_drive(self):
        d=QtWidgets.QFileDialog.getExistingDirectory(self,"Choose DRIVE ROOT (E:\\ → \\\\.\\E:)"); 
        if d: self.edSrc.setText(to_raw_if_drive(d))

    def pick_out(self):
        p=QtWidgets.QFileDialog.getExistingDirectory(self,"Choose output folder"); 
        if p: self.edOut.setText(p)

    def start_scan(self):
        src=self.edSrc.text().strip(); out=self.edOut.text().strip()
        if not src or not out: 
            QtWidgets.QMessageBox.warning(self,"Missing","Pick source and output"); return
        opts=dict(
            chunk=self._b(self.edChunk.text()), overlap=self._b(self.edOv.text()),
            max_bytes=self._b(self.edMaxB.text()), min_size=self._b(self.edMin.text()),
            max_files=self.spMax.value(), fast_index=self.ckFast.isChecked(), dedup=self.ckDedup.isChecked()
        )
        self.table.setRowCount(0); self.pb.setValue(0); self.lbl.setText("Scanning...")
        self.worker=Worker(src,out,opts); self.thread=QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_prog); self.worker.hit.connect(self._on_hit)
        self.worker.done.connect(self._on_done); self.worker.error.connect(self._on_err)
        self.thread.start()

    def _b(self,s): 
        s=(s or "0").lower(); m=1
        if s.endswith("k"): m=1024; s=s[:-1]
        elif s.endswith("m"): m=1024*1024; s=s[:-1]
        elif s.endswith("g"): m=1024*1024*1024; s=s[:-1]
        try: return int(float(s)*m)
        except: return 0

    @QtCore.Slot(object, object)
    def _on_prog(self,c,t):
        c,t=int(c or 0),int(t or 0)
        self.lbl.setText(f"Scanned {c:,}/{t or '?'} bytes")
        if t>0:
            pct=min(100,(c*100)//t); self.pb.setMaximum(100); self.pb.setValue(pct)

    @QtCore.Slot(object)
    def _on_hit(self,r):
        row=self.table.rowCount(); self.table.insertRow(row)
        for col,val in enumerate([r.sig.name,r.start,r.end-r.start,r.out_path,r.ok,r.note]):
            self.table.setItem(row,col,QtWidgets.QTableWidgetItem(str(val)))

    @QtCore.Slot()
    def _on_done(self): self.lbl.setText("Done.")

    @QtCore.Slot(str)
    def _on_err(self,msg): QtWidgets.QMessageBox.critical(self,"Error",msg)

    def _ctx_menu(self,pos):
        menu=QtWidgets.QMenu(self)
        act=menu.addAction("Preview")
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
