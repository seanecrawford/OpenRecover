import os, sys, threading, time
from PySide6 import QtCore, QtGui, QtWidgets

from .carver import FileCarver
from .signatures import ALL_SIGNATURES
from .rawio import to_raw_if_drive
# If you want %/ETA on raw disks too, we’ll try to read length via RawDevice
try:
    from .rawio import RawDevice
except Exception:
    RawDevice = None

APP = "OpenRecover Pro v0.7 (Qt)"

QSS = """
* { font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; font-size: 10.5pt; }
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

def _fmt_bytes(n: int) -> str:
    if n <= 0: return "0 B"
    units=("B","KB","MB","GB","TB","PB"); i=0; v=float(n)
    while v >= 1024 and i < len(units)-1: v/=1024; i+=1
    return f"{v:.1f} {units[i]}"

class Worker(QtCore.QObject):
    # Use Python objects to avoid 32-bit overflow
    progress = QtCore.Signal(object, object)  # (current_bytes, total_bytes or 0)
    done     = QtCore.Signal(list)
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
                progress_cb=lambda c,t: self.progress.emit(c, t),
                deduplicate=self.opts["dedup"]
            )
            res = carver.scan()
            self.done.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class _Relay(QtCore.QObject):
    sig = QtCore.Signal(object, object)  # (current, total)

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.setMinimumSize(1120,740)
        self._relay = _Relay()
        self._relay.sig.connect(self._on_prog)
        self._ui()
        self._speed_state = {"last_c": 0, "last_t": time.monotonic()}

    def _ui(self):
        cw = QtWidgets.QWidget(); self.setCentralWidget(cw)
        root = QtWidgets.QVBoxLayout(cw); root.setContentsMargins(14,14,14,14); root.setSpacing(12)

        top = QtWidgets.QFrame(objectName="Card")
        ops = QtWidgets.QFrame(objectName="Card")
        tbl = QtWidgets.QFrame(objectName="Card")
        for f in (top, ops, tbl):
            f.setFrameStyle(QtWidgets.QFrame.StyledPanel); root.addWidget(f, 0 if f is not tbl else 1)

        # --- top: Source/Output ---
        g = QtWidgets.QGridLayout(top); g.setContentsMargins(16,16,16,16); g.setHorizontalSpacing(10)
        self.edSrc = QtWidgets.QLineEdit(placeholderText="Pick an image (File...) or a Drive (Drive...)")
        self.edOut = QtWidgets.QLineEdit()
        bFile  = QtWidgets.QPushButton("File...")
        bDrive = QtWidgets.QPushButton("Drive...")
        bOut   = QtWidgets.QPushButton("Browse")
        bFile.clicked.connect(self.pick_file); bDrive.clicked.connect(self.pick_drive); bOut.clicked.connect(self.pick_out)
        g.addWidget(QtWidgets.QLabel("Source"), 0,0); g.addWidget(self.edSrc, 0,1,1,3); g.addWidget(bFile, 0,4); g.addWidget(bDrive, 0,5)
        g.addWidget(QtWidgets.QLabel("Output"), 1,0); g.addWidget(self.edOut, 1,1,1,3); g.addWidget(bOut,   1,4,1,2)

        # --- ops: options + actions ---
        og = QtWidgets.QGridLayout(ops); og.setContentsMargins(16,16,16,16); og.setHorizontalSpacing(10)
        self.edChunk = QtWidgets.QLineEdit("16M")
        self.edOv    = QtWidgets.QLineEdit("256K")
        self.edMaxB  = QtWidgets.QLineEdit("0")
        self.edMin   = QtWidgets.QLineEdit("256")
        self.spMax   = QtWidgets.QSpinBox(); self.spMax.setRange(0,10_000_000); self.spMax.setValue(0)
        self.ckFast  = QtWidgets.QCheckBox("Fast index")
        self.ckAllow = QtWidgets.QCheckBox("Allow same-disk (unsafe)")
        self.ckDedup = QtWidgets.QCheckBox("Deduplicate"); self.ckDedup.setChecked(True)
        self.btnImage= QtWidgets.QPushButton("Create Image...")
        self.btnScan = QtWidgets.QPushButton("Start Scan"); self.btnScan.setObjectName("Primary")

        r=0
        og.addWidget(QtWidgets.QLabel("Chunk"), r,0); og.addWidget(self.edChunk, r,1)
        og.addWidget(QtWidgets.QLabel("Overlap"), r,2); og.addWidget(self.edOv,    r,3)
        og.addWidget(QtWidgets.QLabel("Max bytes"), r,4); og.addWidget(self.edMaxB, r,5)
        og.addWidget(QtWidgets.QLabel("Min size"),  r,6); og.addWidget(self.edMin,  r,7)
        og.addWidget(QtWidgets.QLabel("Max files"), r,8); og.addWidget(self.spMax,  r,9)
        r=1
        og.addWidget(self.ckFast,  r,0,1,2); og.addWidget(self.ckAllow, r,2,1,3); og.addWidget(self.ckDedup, r,5,1,2)
        og.addItem(QtWidgets.QSpacerItem(40,10,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), r,7,1,2)
        og.addWidget(self.btnImage, r,9); og.addWidget(self.btnScan, r,10)

        self.btnScan.clicked.connect(self.start_scan)
        self.btnImage.clicked.connect(self.create_image)

        # --- table / progress ---
        vg = QtWidgets.QVBoxLayout(tbl); vg.setContentsMargins(16,16,16,16); vg.setSpacing(10)
        self.pb  = QtWidgets.QProgressBar(); self.pb.setMinimum(0); self.pb.setMaximum(0)  # busy until we know total
        self.lbl = QtWidgets.QLabel("Idle")
        hh = QtWidgets.QHBoxLayout(); hh.addWidget(self.pb,1); hh.addWidget(self.lbl)
        vg.addLayout(hh)

        self.table = QtWidgets.QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(["type","start","length","path","ok","note"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        vg.addWidget(self.table,1)

        tip = QtWidgets.QLabel("Tip: Use Drive... to select E: and scan \\\\.\\E: (Admin EXE). Or Create Image... and scan the .img without admin.")
        tip.setStyleSheet("color:#9AA3B2;")
        vg.addWidget(tip)

    # ---------- pickers ----------
    def pick_file(self):
        p = QtWidgets.QFileDialog.getOpenFileName(self, "Choose disk IMAGE file", "", "Images (*.img *.dd *.bin *.raw *.iso);;All files (*.*)")[0]
        if p: self.edSrc.setText(p)

    def pick_drive(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, r"Choose DRIVE ROOT (select E:\ to scan \\.\E:)")
        if d: self.edSrc.setText(to_raw_if_drive(d))

    def pick_out(self):
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose output folder")
        if p: self.edOut.setText(p)

    # ---------- scan ----------
    def start_scan(self):
        src = self.edSrc.text().strip()
        out = self.edOut.text().strip()
        if not src:
            QtWidgets.QMessageBox.warning(self,"Missing", r"Pick an image, or pick a drive (\\.\E:)")
            return
        src = to_raw_if_drive(src)
        if src.startswith("\\\\.\\") and os.name=="nt":
            # needs Admin EXE
            try:
                import ctypes
                if ctypes.windll.shell32.IsUserAnAdmin()==0:
                    QtWidgets.QMessageBox.warning(self,"Admin required","Use the Admin EXE for raw disks.")
                    return
            except Exception:
                pass
        if not out:
            QtWidgets.QMessageBox.warning(self,"Missing","Choose an output folder"); return

        # reset UI
        self.table.setRowCount(0)
        self.pb.setValue(0)
        self.lbl.setText("Scanning...")

        # seed known total for %/ETA when possible
        self._total_hint = 0
        try:
            if not src.startswith("\\\\.\\"):
                self._total_hint = os.path.getsize(src)
            elif RawDevice is not None:
                try:
                    dev = RawDevice(src, 4096)
                    self._total_hint = int(dev.length or 0)
                    dev.close()
                except Exception:
                    self._total_hint = 0
        except Exception:
            self._total_hint = 0

        if self._total_hint > 0:
            self.pb.setMaximum(1000)  # 0..1000 (0.1% steps)
        else:
            self.pb.setMaximum(0)     # busy mode

        # parse options
        def _b(s:str) -> int:
            s=(s or "0").strip().lower()
            if s in ("0","","none"): return 0
            m=1
            if s.endswith("k"): m=1024; s=s[:-1]
            elif s.endswith("m"): m=1024*1024; s=s[:-1]
            elif s.endswith("g"): m=1024*1024*1024; s=s[:-1]
            try: return int(float(s)*m)
            except Exception: return 0

        opts = dict(
            chunk=_b(self.edChunk.text()),
            overlap=_b(self.edOv.text()),
            max_bytes=_b(self.edMaxB.text()),
            min_size=_b(self.edMin.text()),
            max_files=self.spMax.value(),
            fast_index=self.ckFast.isChecked(),
            dedup=self.ckDedup.isChecked(),
        )

        # worker thread
        self.worker = Worker(src, out, opts)
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_prog)
        self.worker.done.connect(self._on_done)
        self.worker.error.connect(self._on_err)
        self.thread.start()

    @QtCore.Slot(object, object)
    def _on_prog(self, c, t):
        """
        Update progress bar with percent + ETA.
        c,t may be large Python ints; keep everything in Python space.
        """
        try: c = int(c or 0)
        except Exception: c = 0
        try: t = int(t or 0)
        except Exception: t = 0

        # If worker couldn't supply t but we have a file-size hint, use it
        if t == 0 and getattr(self, "_total_hint", 0) > 0:
            t = self._total_hint

        # speed & ETA
        now = time.monotonic()
        dt  = max(1e-6, now - self._speed_state["last_t"])
        dc  = max(0, c - self._speed_state["last_c"])
        speed = dc / dt                  # bytes / sec
        self._speed_state.update(last_c=c, last_t=now)

        if t > 0:
            self.pb.setMaximum(1000)
            pct = min(1000, max(0, (c * 1000) // t))
            self.pb.setValue(pct)
            eta = ""
            if speed > 1e-6:
                remain = max(0, t - c)
                secs   = int(remain / speed)
                m, s   = divmod(secs, 60)
                h, m   = divmod(m, 60)
                eta    = f" • ETA {h:d}:{m:02d}:{s:02d}"
            self.lbl.setText(f"Scanned {_fmt_bytes(c)}/{_fmt_bytes(t)} ({pct/10:.1f}%) • {_fmt_bytes(int(speed))}/s{eta}")
        else:
            # unknown total → busy
            self.pb.setMaximum(0)
            self.lbl.setText(f"Scanned {c:,} bytes")

    @QtCore.Slot(list)
    def _on_done(self, results:list):
        self.lbl.setText(f"Done. {len(results)} files.")
        for r in results:
            row = self.table.rowCount(); self.table.insertRow(row)
            for col,val in enumerate([r.sig.name, r.start, r.end-r.start, r.out_path, r.ok, r.note]):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(str(val)))
        if hasattr(self,"thread"):
            self.thread.quit(); self.thread.wait(2000)

    @QtCore.Slot(str)
    def _on_err(self, msg:str):
        QtWidgets.QMessageBox.critical(self, "Error", msg)
        if hasattr(self,"thread"):
            self.thread.quit(); self.thread.wait(2000)

    # ---------- imaging ----------
    def create_image(self):
        src = self.edSrc.text().strip()
        if not src:
            QtWidgets.QMessageBox.information(self,"Info", r"Pick a drive with Drive... or type \\.\E:")
            return
        src = to_raw_if_drive(src)
        if src.startswith("\\\\.\\") and os.name=="nt":
            try:
                import ctypes
                if ctypes.windll.shell32.IsUserAnAdmin()==0:
                    QtWidgets.QMessageBox.warning(self,"Admin required","Raw volumes require Administrator. Use the Admin build.")
                    return
            except Exception:
                pass
        out, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save raw image as", "", "Raw image (*.img)")
        if not out: return
        self._image_worker(src, out)

    def _image_worker(self, src:str, out:str):
        self.lbl.setText("Imaging...")
        # % mode when we know total, else busy
        total_len = 0
        if src.startswith("\\\\.\\") and RawDevice is not None:
            try:
                dev = RawDevice(src, 4096); total_len = int(dev.length or 0); dev.close()
            except Exception:
                total_len = 0
        self.pb.setMaximum(1000 if total_len>0 else 0); self.pb.setValue(0)

        def job():
            try:
                total = 0
                if src.startswith("\\\\.\\") and RawDevice is not None:
                    dev = RawDevice(src, 4096); length = int(dev.length or 0)
                    sizes = [1024*1024, 256*1024, 64*1024, 4096]
                    with open(out, "wb") as f:
                        pos = 0
                        while True:
                            try:
                                data = dev.read_at(pos, sizes[0])
                            except Exception:
                                data = b""
                                for s in sizes[1:]:
                                    try: data = dev.read_at(pos, s); break
                                    except Exception: data = b""
                                if not data:
                                    pos += 4096  # skip bad 4 KiB and continue
                                    continue
                            if not data: break
                            f.write(data); pos += len(data); total += len(data)
                            # emit progress (object types → no overflow)
                            self._relay.sig.emit(total, length)
                    dev.close()
                else:
                    with open(src,"rb") as fi, open(out,"wb") as fo:
                        while True:
                            b = fi.read(1024*1024)
                            if not b: break
                            fo.write(b); total += len(b)
                            self._relay.sig.emit(total, 0)  # busy mode
                QtCore.QMetaObject.invokeMethod(self.lbl, "setText", QtCore.Qt.QueuedConnection,
                                                QtCore.Q_ARG(str, "Imaging complete."))
            except Exception as e:
                QtCore.QMetaObject.invokeMethod(self, "_on_err", QtCore.Qt.QueuedConnection,
                                                QtCore.Q_ARG(str, str(e)))
        threading.Thread(target=job, daemon=True).start()

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = Main(); w.show()
    sys.exit(app.exec())
