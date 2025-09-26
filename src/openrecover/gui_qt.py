import os, sys, time, threading
from typing import Optional, List
from PySide6 import QtCore, QtGui, QtWidgets

from .carver import FileCarver, CarveResult
from .signatures import ALL_SIGNATURES
from .rawio import to_raw_if_drive, RawDevice

APP_TITLE = "OpenRecover Pro v0.7 (Qt)"
GREEN = "#4ade80"

def _asset_path(name: str) -> str:
    """
    Resolve asset in both source and frozen EXE.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    # When frozen, openrecover/* is unpacked under _MEIPASS
    # When running from source, this module sits in src/openrecover/
    p1 = os.path.join(base, "openrecover", "assets", name)
    p2 = os.path.join(base, "assets", name)
    return p1 if os.path.exists(p1) else p2

QSS = f"""
* {{ font-family:'Segoe UI','Inter','Roboto'; font-size: 10.5pt; }}
QMainWindow {{ background:#0F1115; }}
QWidget     {{ color:#E6E9EF; background:#0F1115; }}
QFrame#Card {{ background:#171A21; border:1px solid #232733; border-radius:12px; }}
QPushButton {{ background:#232733; border:1px solid #2F3542; border-radius:8px; padding:6px 10px; }}
QPushButton:hover {{ background:#2A3140; }}
QPushButton#Primary {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3B82F6,stop:1 #22D3EE); border:none; color:white; font-weight:600; }}
QLineEdit   {{ background:#0B0D11; border:1px solid #2A3040; border-radius:6px; padding:6px 8px; }}
QSpinBox    {{ background:#0B0D11; border:1px solid #2A3040; border-radius:6px; padding:6px 8px; color:#E6E9EF; }}
QProgressBar {{ border:1px solid #2A3040; border-radius:8px; background:#0B0D11; text-align:center; color:#AAB1BD; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22D3EE,stop:1 #3B82F6); border-radius:8px; }}
QHeaderView::section {{ background:#171A21; border:1px solid #232733; padding:6px; }}
QTableWidget {{ gridline-color:#232733; selection-background-color:#3B82F6; }}
"""

class ScanWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)             # cur, total
    item     = QtCore.Signal(object)               # CarveResult
    done     = QtCore.Signal()
    error    = QtCore.Signal(str)

    def __init__(self, src: str, out: str, opts: dict):
        super().__init__()
        self.src = src; self.out = out; self.opts = opts
        self._stop = False
        self._pause = False

    @QtCore.Slot()
    def run(self):
        try:
            def stopf(): return self._stop
            def pausef(): return self._pause
            c = FileCarver(
                self.src, self.out, ALL_SIGNATURES,
                chunk=self.opts["chunk"],
                overlap=self.opts["overlap"],
                max_files=self.opts["max_files"],
                fast_index=False,
                max_bytes=self.opts["max_bytes"],
                min_size=self.opts["min_size"],
                start_offset=self.opts["start"],
                deduplicate=self.opts["dedup"],
                progress_cb=lambda a,b: self.progress.emit(int(a), int(b)),
                stop_flag=stopf,
                pause_flag=pausef,
            )
            for r in c.scan():
                self.item.emit(r)
                if self._stop:
                    break
            c.close()
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):  self._stop  = True
    def pause(self): self._pause = True
    def resume(self): self._pause = False

class ImageWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    done     = QtCore.Signal(str)
    error    = QtCore.Signal(str)

    def __init__(self, src: str, out_img: str):
        super().__init__()
        self.src = src
        self.out_img = out_img
        self._stop = False

    @QtCore.Slot()
    def run(self):
        try:
            src = self.src.strip()
            src = to_raw_if_drive(src)
            total = 0
            if os.name=="nt" and src.startswith(r"\\.\\".rstrip("\\")):
                dev = RawDevice(src, 4096)
                length = dev.length or 0
                with open(self.out_img, "wb") as fo:
                    pos = 0
                    bs_list = [1024*1024, 256*1024, 64*1024, 4096]
                    while not self._stop:
                        data = b""
                        ok = False
                        for b in bs_list:
                            try:
                                data = dev.read_at(pos, b)
                                ok = True; break
                            except Exception:
                                ok = False; continue
                        if not ok or not data:
                            break
                        fo.write(data); pos += len(data); total += len(data)
                        self.progress.emit(int(total), int(length))
                dev.close()
            else:
                with open(src, "rb") as fi, open(self.out_img, "wb") as fo:
                    fi.seek(0, os.SEEK_END); length = fi.tell(); fi.seek(0)
                    while not self._stop:
                        data = fi.read(1024*1024)
                        if not data: break
                        fo.write(data); total += len(data)
                        self.progress.emit(int(total), int(length))
            self.done.emit(self.out_img)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self): self._stop = True

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1120, 740)
        self._ui()
        self._thread = None
        self._worker = None

    def _ui(self):
        self.setStyleSheet(QSS)
        cw = QtWidgets.QWidget(); self.setCentralWidget(cw)
        v = QtWidgets.QVBoxLayout(cw); v.setContentsMargins(10,10,10,10); v.setSpacing(10)

        # Header w/ logo
        topbar = QtWidgets.QHBoxLayout(); v.addLayout(topbar)
        logo_path = _asset_path("spriglogo.png")
        if os.path.exists(logo_path):
            pm = QtGui.QPixmap(logo_path)
            lbl_logo = QtWidgets.QLabel(); lbl_logo.setPixmap(pm.scaledToHeight(26, QtCore.Qt.SmoothTransformation))
            topbar.addWidget(lbl_logo, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        title = QtWidgets.QLabel("Sprig")
        title.setStyleSheet(f"color:{GREEN}; font-size:18pt; font-weight:700; margin-left:8px;")
        topbar.addWidget(title, 0, QtCore.Qt.AlignLeft)
        topbar.addStretch(1)

        # Card: source/output
        card1 = QtWidgets.QFrame(objectName="Card"); v.addWidget(card1)
        g1 = QtWidgets.QGridLayout(card1); g1.setContentsMargins(12,12,12,12); g1.setHorizontalSpacing(10)
        self.edSrc = QtWidgets.QLineEdit()
        self.edOut = QtWidgets.QLineEdit()
        btnFile = QtWidgets.QPushButton("File…")
        btnDrive= QtWidgets.QPushButton("Drive…")
        btnOut  = QtWidgets.QPushButton("Browse")
        btnFile.clicked.connect(self._pick_file)
        btnDrive.clicked.connect(self._pick_drive)
        btnOut.clicked.connect(self._pick_out)

        g1.addWidget(QtWidgets.QLabel("Source"),0,0); g1.addWidget(self.edSrc,0,1,1,3); g1.addWidget(btnFile,0,4); g1.addWidget(btnDrive,0,5)
        g1.addWidget(QtWidgets.QLabel("Output"),1,0); g1.addWidget(self.edOut,1,1,1,3); g1.addWidget(btnOut,1,4)

        # Card: options + actions
        card2 = QtWidgets.QFrame(objectName="Card"); v.addWidget(card2)
        g2 = QtWidgets.QGridLayout(card2); g2.setContentsMargins(12,12,12,12)
        self.edChunk = QtWidgets.QLineEdit("16M")
        self.edOv    = QtWidgets.QLineEdit("256K")
        self.edMaxB  = QtWidgets.QLineEdit("0")
        self.edMin   = QtWidgets.QLineEdit("256")
        self.spMax   = QtWidgets.QSpinBox(); self.spMax.setRange(0, 10_000_000); self.spMax.setValue(0)
        self.ckFast  = QtWidgets.QCheckBox("Fast index"); self.ckFast.setChecked(False)
        self.ckSame  = QtWidgets.QCheckBox("Allow same-disk (unsafe)")
        self.ckDedup = QtWidgets.QCheckBox("Deduplicate"); self.ckDedup.setChecked(True)

        g2.addWidget(QtWidgets.QLabel("Chunk"),0,0); g2.addWidget(self.edChunk,0,1)
        g2.addWidget(QtWidgets.QLabel("Overlap"),0,2); g2.addWidget(self.edOv,0,3)
        g2.addWidget(QtWidgets.QLabel("Max bytes"),0,4); g2.addWidget(self.edMaxB,0,5)
        g2.addWidget(QtWidgets.QLabel("Min size"),0,6); g2.addWidget(self.edMin,0,7)
        g2.addWidget(QtWidgets.QLabel("Max files"),0,8); g2.addWidget(self.spMax,0,9)
        g2.addWidget(self.ckFast,1,0,1,2); g2.addWidget(self.ckSame,1,2,1,3); g2.addWidget(self.ckDedup,1,5,1,2)

        self.btnImage = QtWidgets.QPushButton("Create Image…")
        self.btnStart = QtWidgets.QPushButton("Start Scan"); self.btnStart.setObjectName("Primary")
        self.btnPause = QtWidgets.QPushButton("Pause")
        self.btnStop  = QtWidgets.QPushButton("Stop")
        g2.addWidget(self.btnImage,1,8); g2.addWidget(self.btnStart,1,9); g2.addWidget(self.btnPause,1,10); g2.addWidget(self.btnStop,1,11)

        self.btnImage.clicked.connect(self._create_image)
        self.btnStart.clicked.connect(self._start)
        self.btnPause.clicked.connect(self._pause_resume)
        self.btnStop.clicked.connect(self._stop)

        # Progress
        self.pb = QtWidgets.QProgressBar(); self.pb.setRange(0, 1); self.pb.setValue(0)
        v.addWidget(self.pb)
        self.lbl = QtWidgets.QLabel("Idle"); v.addWidget(self.lbl)

        # Table
        self.tbl = QtWidgets.QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["type","start","length","path","ok","note"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl.doubleClicked.connect(self._open_item)
        v.addWidget(self.tbl, 1)

        # Footer tip
        tip = QtWidgets.QLabel("Tip: Use Drive… to select E:\\ and scan \\\\.\\E: (Admin EXE). Or Create Image… and scan the .img without admin.")
        tip.setStyleSheet("color:#9AA3B2;")
        v.addWidget(tip)

    # ---- small helpers ----
    def _parse_bytes(self, s: str) -> int:
        s = (s or "0").strip().lower()
        if s in ("0","","none"): return 0
        m=1
        if s.endswith("k"): m=1024; s=s[:-1]
        elif s.endswith("m"): m=1024*1024; s=s[:-1]
        elif s.endswith("g"): m=1024*1024*1024; s=s[:-1]
        try: return int(float(s)*m)
        except: return 0

    # ---- browse actions ----
    def _pick_file(self):
        p,_ = QtWidgets.QFileDialog.getOpenFileName(self,"Choose image file")
        if p: self.edSrc.setText(p)

    def _pick_drive(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, r"Choose DRIVE ROOT (select E:\ to scan \\.\E:)")
        if d:
            self.edSrc.setText(to_raw_if_drive(d))

    def _pick_out(self):
        p = QtWidgets.QFileDialog.getExistingDirectory(self,"Choose output folder")
        if p: self.edOut.setText(p)

    # ---- imaging ----
    def _create_image(self):
        src = self.edSrc.text().strip()
        if not src:
            QtWidgets.QMessageBox.information(self,"Info",r"Pick a drive with Drive… or type \\.\E:")
            return
        out, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save raw image as","","Raw image (*.img)")
        if not out: return
        self.pb.setRange(0,1); self.pb.setValue(0); self.lbl.setText("Imaging…")
        self._img_thread = QtCore.QThread(self)
        self._img_worker = ImageWorker(src, out)
        self._img_worker.moveToThread(self._img_thread)
        self._img_thread.started.connect(self._img_worker.run)
        self._img_worker.progress.connect(self._on_prog)
        self._img_worker.done.connect(lambda p: (self._img_thread.quit(), self._img_thread.wait(), self.lbl.setText(f"Image saved: {p}")))
        self._img_worker.error.connect(self._err)
        self._img_thread.start()

    # ---- scanning ----
    def _start(self):
        src = self.edSrc.text().strip()
        out = self.edOut.text().strip()
        if not src:
            QtWidgets.QMessageBox.warning(self,"Missing",r"Pick a source (image file or \\.\E:)")
            return
        if not out:
            QtWidgets.QMessageBox.warning(self,"Missing","Choose an output folder")
            return
        # Basic safety: warn if output seems to be on same disk (user can override)
        if not self.ckSame.isChecked() and os.name=="nt" and src.startswith(r"\\.\\".rstrip("\\")):
            QtWidgets.QMessageBox.warning(self,"Safety","Output on the same physical disk can cause overwrites. Tick 'Allow same-disk' to continue.")
            return

        opts = dict(
            chunk=self._parse_bytes(self.edChunk.text()),
            overlap=self._parse_bytes(self.edOv.text()),
            max_bytes=self._parse_bytes(self.edMaxB.text()),
            min_size=self._parse_bytes(self.edMin.text()),
            max_files=int(self.spMax.value()),
            start=0,
            dedup=self.ckDedup.isChecked(),
        )

        self.tbl.setRowCount(0)
        self.pb.setRange(0, 100); self.pb.setValue(0)
        self.lbl.setText("Scanning…")
        self.btnStart.setEnabled(False)

        self._thread = QtCore.QThread(self)
        self._worker = ScanWorker(src, out, opts)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_prog)
        self._worker.item.connect(self._on_item)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._err)
        self._thread.start()

    def _pause_resume(self):
        if not self._worker: return
        if self.btnPause.text()=="Pause":
            self._worker.pause(); self.btnPause.setText("Resume"); self.lbl.setText("Paused")
        else:
            self._worker.resume(); self.btnPause.setText("Pause"); self.lbl.setText("Scanning…")

    def _stop(self):
        if self._worker:
            self._worker.stop()

    # ---- UI sinks ----
    @QtCore.Slot(int,int)
    def _on_prog(self, cur: int, total: int):
        # compute percent + ETA
        if not hasattr(self, "_time_mark"):
            self._time_mark = time.time(); self._pos_mark = cur
        now = time.time(); dt = max(0.001, now - getattr(self, "_time_mark", now))
        sp = (cur - getattr(self, "_pos_mark", 0)) / dt
        if sp < 1: sp = 1
        if total > 0:
            pct = int(min(100, max(0, cur*100//total)))
            self.pb.setValue(pct)
            remain = (total - cur) / sp
            self.lbl.setText(f"Scanned {cur:,}/{total:,} ({pct}%) • {sp/1024/1024:.1f} MB/s • ETA {int(remain//60)}m{int(remain%60)}s")
        else:
            self.pb.setRange(0,0)
            self.lbl.setText(f"Scanned {cur:,} • {sp/1024/1024:.1f} MB/s")

        self._time_mark = now; self._pos_mark = cur

    @QtCore.Slot(object)
    def _on_item(self, r: CarveResult):
        row = self.tbl.rowCount(); self.tbl.insertRow(row)
        vals = [r.sig.name, str(r.start), str(r.end-r.start), r.out_path, str(r.ok), r.note]
        for col, val in enumerate(vals):
            it = QtWidgets.QTableWidgetItem(val)
            self.tbl.setItem(row, col, it)

    @QtCore.Slot()
    def _on_done(self):
        self.btnStart.setEnabled(True)
        self.lbl.setText("Done")

    @QtCore.Slot(str)
    def _err(self, msg: str):
        QtWidgets.QMessageBox.critical(self,"Error", msg)

    def _open_item(self):
        rows = self.tbl.selectionModel().selectedRows()
        if not rows: return
        r = rows[0].row()
        path = self.tbl.item(r, 3).text()
        if os.path.exists(path):
            if os.name=="nt":
                os.startfile(path)
            else:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = Main()
    w.show()
    sys.exit(app.exec())
