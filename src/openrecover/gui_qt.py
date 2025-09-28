from __future__ import annotations
import os, time, threading, traceback
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QObject, QThread, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QCheckBox, QSpinBox, QProgressBar, QTableWidget,
    QTableWidgetItem, QGridLayout, QHBoxLayout, QVBoxLayout, QMessageBox
)

from .carver import FileCarver
from .signatures import ALL_SIGNATURES
from .rawio import to_raw_if_drive

_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
_LOGO = os.path.join(_ASSET_DIR, "spriglogo.png")

APP_NAME = "Sprig OpenRecover"
QSS = """
*{font-family: 'Segoe UI','Inter','Roboto'; font-size:10.5pt;}
QMainWindow{background:#0F1115;}
QWidget{color:#E6E9EF;background:#0F1115;}
QLabel#Brand{color:#7BF79E;font-weight:700;font-size:18pt;}
QFrame#Card{background:#171A21;border:1px solid #232733;border-radius:12px;}
QLineEdit{background:#0B0D11;border:1px solid #2A3040;border-radius:6px;padding:6px;}
QPushButton{background:#232733;border:1px solid #2F3542;border-radius:8px;padding:8px 14px;}
QPushButton:disabled{opacity:.5;}
QPushButton#Primary{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22D3EE,stop:1 #3B82F6);border:none;color:white;font-weight:600;}
QProgressBar{border:1px solid #2A3040;border-radius:8px;background:#0B0D11;text-align:center;color:#AAB1BD;height:18px;}
QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22D3EE,stop:1 #3B82F6);border-radius:8px;}
QHeaderView::section{background:#171A21;border:1px solid #232733;padding:6px;}
QTableWidget{gridline-color:#232733;selection-background-color:#3B82F6;}
"""

class Worker(QObject):
    progress = Signal(int, int)
    found    = Signal(object)
    status   = Signal(str)
    error    = Signal(str)
    done     = Signal()

    def __init__(self, src: str, out: str, opts: dict):
        """
        Create a new worker.

        Parameters
        ----------
        src : str
            Source image or raw device path.
        out : str
            Directory where carved files will be written.
        opts : dict
            Options dictionary. In addition to numeric and boolean
            values, this may include a 'signatures' key listing the
            FileSignature objects to scan for.
        """
        super().__init__()
        self.src = src
        self.out = out
        self.opts = opts
        self.signatures = opts.get('signatures', ALL_SIGNATURES)
        self._pause = threading.Event()
        self._stop = threading.Event()
        self._pause.clear()
        self._stop.clear()

    @Slot()
    def run(self):
        """
        Run the carving process in a worker thread.
        """
        try:
            self.status.emit("Initializing...")
            carver = FileCarver(
                self.src,
                self.out,
                self.signatures,
                chunk=self.opts["chunk"],
                overlap=self.opts["overlap"],
                max_files=self.opts["max_files"],
                fast_index=self.opts["fast_index"],
                max_bytes=self.opts["max_bytes"],
                min_size=self.opts["min_size"],
                progress_cb=lambda cur, total: self.progress.emit(int(cur), int(total)),
                deduplicate=self.opts["dedup"]
            )
            self.status.emit("Scanning…")
            for r in carver.scan():
                if self._stop.is_set():
                    self.status.emit("Stopped")
                    break
                while self._pause.is_set():
                    time.sleep(0.05)
                self.found.emit(r)
            self.done.emit()
        except Exception:
            self.error.emit(traceback.format_exc())

    def pause(self, yes: bool):
        if yes:
            self._pause.set()
        else:
            self._pause.clear()

    def stop(self):
        self._stop.set()

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v0.7 (Qt)")
        self.setMinimumSize(1000, 620)
        self._build_ui()
        self._wire()
        self._reset_state()

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12,12,12,12)
        outer.setSpacing(10)

        brand_row = QHBoxLayout()
        if os.path.exists(_LOGO):
            logo = QLabel()
            pix = QPixmap(_LOGO)
            if not pix.isNull():
                logo.setPixmap(pix.scaledToHeight(28, Qt.SmoothTransformation))
                brand_row.addWidget(logo)
        self.lblBrand = QLabel(" Sprig", objectName="Brand")
        brand_row.addWidget(self.lblBrand)
        brand_row.addStretch(1)
        outer.addLayout(brand_row)

        io_card = QWidget(objectName="Card")
        io = QGridLayout(io_card)
        io.setContentsMargins(12,12,12,12)
        self.edSrc = QLineEdit()
        self.edOut = QLineEdit()
        self.btnFile = QPushButton("File…")
        self.btnDrive = QPushButton("Drive…")
        self.btnOut = QPushButton("Browse")
        r = 0
        io.addWidget(QLabel("Source"), r, 0)
        io.addWidget(self.edSrc, r, 1, 1, 3)
        io.addWidget(self.btnFile, r, 4)
        io.addWidget(self.btnDrive, r, 5)
        r = 1
        io.addWidget(QLabel("Output"), r, 0)
        io.addWidget(self.edOut, r, 1, 1, 3)
        io.addWidget(self.btnOut, r, 4)
        outer.addWidget(io_card)

        opt_card = QWidget(objectName="Card")
        opt = QGridLayout(opt_card)
        opt.setContentsMargins(12,12,12,12)
        self.edChunk = QLineEdit("16M")
        self.edOverlap = QLineEdit("256K")
        self.edMaxBytes = QLineEdit("0")
        self.edMinSize = QLineEdit("256")
        self.spMaxFiles = QSpinBox()
        self.spMaxFiles.setRange(0, 10_000_000)
        self.spMaxFiles.setValue(0)
        self.ckFast = QCheckBox("Fast index")
        self.ckAllow = QCheckBox("Allow same-disk (unsafe)")
        self.ckDedup = QCheckBox("Deduplicate")
        self.ckDedup.setChecked(True)
        self.btnImage = QPushButton("Create Image…")
        self.btnStart = QPushButton("Start Scan", objectName="Primary")
        self.btnPause = QPushButton("Pause")
        self.btnStop = QPushButton("Stop")
        self.btnPause.setEnabled(False)
        self.btnStop.setEnabled(False)

        c = 0
        opt.addWidget(QLabel("Chunk"), 0, c); c += 1
        opt.addWidget(self.edChunk, 0, c); c += 1
        opt.addWidget(QLabel("Overlap"), 0, c); c += 1
        opt.addWidget(self.edOverlap, 0, c); c += 1
        opt.addWidget(QLabel("Max bytes"), 0, c); c += 1
        opt.addWidget(self.edMaxBytes, 0, c); c += 1
        opt.addWidget(QLabel("Min size"), 0, c); c += 1
        opt.addWidget(self.edMinSize, 0, c); c += 1
        opt.addWidget(QLabel("Max files"), 0, c); c += 1
        opt.addWidget(self.spMaxFiles, 0, c); c += 1
        opt.addWidget(self.ckFast, 1, 0, 1, 2)
        opt.addWidget(self.ckAllow, 1, 2, 1, 3)
        opt.addWidget(self.ckDedup, 1, 5, 1, 2)

        # File type selection checkboxes
        self.sig_checkboxes = {}
        sig_layout = QHBoxLayout()
        for sig in ALL_SIGNATURES:
            chk = QCheckBox(sig.name.upper())
            chk.setChecked(True)
            self.sig_checkboxes[sig.name] = (chk, sig)
            sig_layout.addWidget(chk)
        sig_container = QWidget()
        sig_container.setLayout(sig_layout)
        opt.addWidget(sig_container, 2, 0, 1, 6)

        opt.addWidget(self.btnImage, 3, 5)
        opt.addWidget(self.btnStart, 3, 6)
        opt.addWidget(self.btnPause, 3, 7)
        opt.addWidget(self.btnStop, 3, 8)
        outer.addWidget(opt_card)

        self.pb = QProgressBar()
        self.pb.setMinimum(0)
        self.pb.setMaximum(1)
        outer.addWidget(self.pb)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["type","start","length","path","ok","note"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        outer.addWidget(self.tbl, 1)

        self.lblTip = QLabel("Tip: Use Drive… to select E: and scan \\\\ \\\\E: (Admin EXE). Or Create Image… to scan the image without admin.")
        self.lblTip.setStyleSheet("color:#9AA3B2")
        outer.addWidget(self.lblTip)

    def _wire(self):
        self.btnFile.clicked.connect(self._pick_file)
        self.btnDrive.clicked.connect(self._pick_drive)
        self.btnOut.clicked.connect(self._pick_out)
        self.btnStart.clicked.connect(self._start)
        self.btnPause.clicked.connect(self._toggle_pause)
        self.btnStop.clicked.connect(self._stop)
        self.btnImage.clicked.connect(self._create_image)
        self._eta_timer = QTimer(self)
        self._eta_timer.setInterval(750)
        self._eta_timer.timeout.connect(self._refresh_eta)

    def _reset_state(self):
        self._thread: Optional[QThread] = None
        self._worker: Optional[Worker]  = None
        self._last_prog = (0, time.time())
        self._cur = 0
        self._total = 0
        self.pb.setValue(0)
        self.pb.setMaximum(1)
        self.tbl.setRowCount(0)
        self.setWindowTitle(f"{APP_NAME} Ready")

    def _pick_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose disk IMAGE file", "", "Images (*.img *.dd *.bin *.raw *.iso);;All files (*.*)")
        if p:
            self.edSrc.setText(p)

    def _pick_drive(self):
        d = QFileDialog.getExistingDirectory(self, r"Choose DRIVE ROOT (select E:\ to scan \\ \\E:)")
        if d:
            self.edSrc.setText(to_raw_if_drive(d))

    def _pick_out(self):
        p = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if p:
            self.edOut.setText(p)

    def _parse_bytes(self, s: str) -> int:
        s = (s or "0").strip().lower()
        if s in ("0", "", "none"):
            return 0
        mul = 1
        if s.endswith("k"):
            mul = 1024; s = s[:-1]
        elif s.endswith("m"):
            mul = 1024*1024; s = s[:-1]
        elif s.endswith("g"):
            mul = 1024*1024*1024; s = s[:-1]
        return int(float(s) * mul)

    def _start(self):
        src = self.edSrc.text().strip()
        out = self.edOut.text().strip()
        if not src:
            QMessageBox.warning(self, "Missing", r"Pick an image, or pick a drive (\\.\E:)")
            return
        if not out:
            QMessageBox.warning(self, "Missing", "Choose an output folder")
            return
        self.tbl.setRowCount(0)
        self._cur = 0; self._total = 0
        self.pb.setValue(0); self.pb.setMaximum(1)
        self._eta_timer.start()
        self.btnStart.setEnabled(False); self.btnPause.setEnabled(True); self.btnStop.setEnabled(True)
        selected_sigs = [sig for (chk, sig) in self.sig_checkboxes.values() if chk.isChecked()]
        if not selected_sigs:
            QMessageBox.warning(self, "No file types selected", "Please select at least one file type to scan.")
            return
        opts = dict(
            chunk=self._parse_bytes(self.edChunk.text()),
            overlap=self._parse_bytes(self.edOverlap.text()),
            max_bytes=self._parse_bytes(self.edMaxBytes.text()),
            min_size=self._parse_bytes(self.edMinSize.text()),
            max_files=self.spMaxFiles.value(),
            fast_index=self.ckFast.isChecked(),
            dedup=self.ckDedup.isChecked(),
            signatures=selected_sigs,
        )
        self._thread = QThread(self)
        self._worker = Worker(src, out, opts)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.found.connect(self._on_found)
        self._worker.status.connect(lambda s: self.setWindowTitle(f"{APP_NAME} • {s}"))
        self._worker.error.connect(self._on_error)
        self._worker.done.connect(self._on_done)
        self._thread.start()

    def _toggle_pause(self):
        if not self._worker:
            return
        if self.btnPause.text() == "Pause":
            self._worker.pause(True)
            self.btnPause.setText("Resume")
        else:
            self._worker.pause(False)
            self.btnPause.setText("Pause")

    def _stop(self):
        if self._worker:
            self._worker.stop()

    @Slot(int, int)
    def _on_progress(self, cur: int, total: int):
        self._cur = cur; self._total = total
        if total > 0:
            self.pb.setMaximum(total)
            self.pb.setValue(min(cur, total))
        else:
            self.pb.setMaximum(0)

    @Slot(object)
    def _on_found(self, r):
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        def _set(c, v):
            self.tbl.setItem(row, c, QTableWidgetItem(str(v)))
        _set(0, getattr(r.sig, "name", "?"))
        start = getattr(r, "start", 0)
        end   = getattr(r, "end", start)
        _set(1, start)
        _set(2, max(0, end - start))
        _set(3, getattr(r, "out_path", ""))
        _set(4, getattr(r, "ok", False))
        _set(5, getattr(r, "note", ""))

    @Slot()
    def _on_done(self):
        self._eta_timer.stop()
        self.btnStart.setEnabled(True); self.btnPause.setEnabled(False); self.btnStop.setEnabled(False)
        self.btnPause.setText("Pause")
        self.setWindowTitle(f"{APP_NAME} Done")
        if self._thread:
            self._thread.quit(); self._thread.wait(1500)
        self._thread = None; self._worker = None

    @Slot(str)
    def _on_error(self, msg: str):
        self._eta_timer.stop()
        QMessageBox.critical(self, "Error", msg)
        self._on_done()

    def _refresh_eta(self):
        if self._total <= 0 or self._cur <= 0:
            return
        now = time.time()
        cur, last_ts = self._last_prog
        dt = max(0.001, now - last_ts)
        spd = max(1, self._cur - cur) / dt
        rem = max(0, self._total - self._cur)
        eta_s = int(rem / spd) if spd > 0 else 0
        pct = (self._cur / self._total) * 100.0
        self.setWindowTitle(f"{APP_NAME} • {pct:.1f}% • {self._cur/1e9:.2f}/{self._total/1e9:.2f} GB • {spd/1e6:.1f} MB/s • ETA {self._fmt(eta_s)}")
        self._last_prog = (self._cur, now)

    @staticmethod
    def _fmt(s: int) -> str:
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:d}h {m:02d}m"
        if m:
            return f"{m:d}m {s:02d}s"
        return f"{s:d}s"

    def _create_image(self):
        src = self.edSrc.text().strip()
        if not src:
            QMessageBox.information(self, "Info", r"Pick a drive with Drive… or type \\ .\E:")
            return
        src = to_raw_if_drive(src)
        out, _ = QFileDialog.getSaveFileName(self, "Save raw image as", "", "Raw image (*.img)")
        if not out:
            return
        self.setWindowTitle(f"{APP_NAME} • Imaging…")
        self.pb.setMaximum(0); self.pb.setValue(0)
        def job():
            try:
                total = 0
                bs_list = [1024*1024, 256*1024, 64*1024, 4096]
                with open(src, "rb", buffering=0) as fi, open(out, "wb", buffering=0) as fo:
                    while True:
                        try:
                            b = fi.read(bs_list[0])
                        except Exception:
                            b = b""
                            for bs in bs_list[1:]:
                                try:
                                    b = fi.read(bs)
                                    break
                                except Exception:
                                    b = b""
                            if not b:
                                try:
                                    fi.seek(fi.tell() + 4096)
                                except Exception:
                                    break
                                continue
                        if not b:
                            break
                        fo.write(b); total += len(b)
                        self.pb.setMaximum(0)
                self.setWindowTitle(f"{APP_NAME} • Imaging complete")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                self.pb.setMaximum(1); self.pb.setValue(0)
        threading.Thread(target=job, daemon=True).start()

def main() -> int:
    app = QApplication([])
    app.setStyleSheet(QSS)
    w = Main()
    w.show()
    return app.exec()
