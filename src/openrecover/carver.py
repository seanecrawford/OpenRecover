import os, hashlib
from dataclasses import dataclass
from typing import Iterable, Optional, Callable, Tuple
from .rawio import RawDevice, to_raw_if_drive
from .signatures import FileSignature

@dataclass
class CarveResult:
    sig: FileSignature
    start: int
    end: int
    out_path: str
    ok: bool
    note: str

def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _long(p: str) -> str:
    if os.name == "nt":
        ap = os.path.abspath(p)
        if not ap.startswith("\\\\?\\"):
            ap = "\\\\?\\" + ap
        return ap
    return p

class FileCarver:
    """
    Block scanner with overlap + simple signature-based carving.
    """
    def __init__(
        self,
        source: str,
        output_dir: str,
        signatures: Iterable[FileSignature],
        chunk: int = 16 * 1024 * 1024,
        overlap: int = 256 * 1024,
        max_files: int = 0,
        fast_index: bool = False,
        max_bytes: int = 0,
        min_size: int = 256,
        start_offset: int = 0,
        deduplicate: bool = True,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        stop_flag: Optional[Callable[[], bool]] = None,
        pause_flag: Optional[Callable[[], bool]] = None,
    ):
        self.src_str = source
        self.output_dir = output_dir
        self.signatures = list(signatures)
        self.chunk = max(4096, chunk)
        self.overlap = max(0, overlap)
        self.max_files = max_files
        self.fast_index = fast_index
        self.max_bytes = max_bytes
        self.min_size = min_size
        self.start_offset = max(0, start_offset)
        self.dedup = deduplicate
        self.progress_cb = progress_cb or (lambda a,b: None)
        self.stop_flag = stop_flag or (lambda: False)
        self.pause_flag = pause_flag or (lambda: False)
        self._sha_seen: set[str] = set()

        sp = to_raw_if_drive(self.src_str)
        self._is_raw = (sp.startswith(r"\\.\\".rstrip("\\")) and os.name == "nt")
        self._raw = RawDevice(sp) if self._is_raw else None
        self._fin = None
        if not self._is_raw:
            self._fin = open(sp, "rb", buffering=0)

        if self._is_raw:
            self.total = self._raw.length or 0
        else:
            self.total = os.path.getsize(sp)

        if self.max_bytes and self.total:
            self.total = min(self.total, self.max_bytes)

        _ensure_dir(self.output_dir)

    def close(self):
        if self._raw:
            self._raw.close()
        if self._fin:
            self._fin.close()

    def _read_at(self, off: int, size: int) -> bytes:
        if self._is_raw:
            return self._raw.read_at(off, size)
        else:
            self._fin.seek(off, os.SEEK_SET)
            return self._fin.read(size)

    def _emit(self, cur: int):
        self.progress_cb(cur, self.total or 0)

    def _sha256(self, data: bytes) -> str:
        from .utils import sha256 as _sha
        return _sha(data)

    def _write_file(self, subdir: str, name: str, data: bytes) -> Tuple[str, Optional[str]]:
        out_dir = os.path.join(self.output_dir, subdir)
        _ensure_dir(out_dir)
        base = name[:180]
        out_path = os.path.join(out_dir, base)
        try:
            with open(_long(out_path), "wb") as fo:
                fo.write(data)
            return out_path, None
        except Exception as e:
            return out_path, f"write error: {e}"

    def _find_footer(self, blob: bytes, sig: FileSignature, start_idx: int) -> Optional[int]:
        if sig.footer is None:
            return None
        idx = blob.find(sig.footer, start_idx + len(sig.header))
        if idx < 0:
            return None
        if sig is not None and sig.name == "png":
            return idx + len(sig.footer) + 4
        return idx + len(sig.footer)

    def _size_from_iso_bmff(self, blob: bytes, pos: int, sig: FileSignature) -> Optional[int]:
        if not sig.size_from_header_iso_bmff:
            return None
        off, szlen = sig.size_from_header_iso_bmff
        if pos + off + szlen <= len(blob):
            box_size = int.from_bytes(blob[pos+off:pos+off+szlen], "big", signed=False)
            if box_size > 0:
                return box_size
        return None

    def scan(self) -> Iterable[CarveResult]:
        cur = self.start_offset
        produced = 0
        overlap = min(self.overlap, self.chunk // 2)

        while (self.total == 0 or cur < self.total):
            if self.stop_flag():
                break
            while self.pause_flag():
                self._emit(cur)

            size = self.chunk
            if self.total:
                size = min(size, self.total - cur)
                if size <= 0:
                    break
            try:
                buf = self._read_at(cur, size)
            except Exception:
                cur += 4096
                self._emit(cur)
                continue

            if not buf:
                break

            for sig in self.signatures:
                start_index = 0
                while True:
                    i = buf.find(sig.header, start_index)
                    if i < 0:
                        break
                    global_pos = cur + i

                    data = b""
                    end_pos = None
                    end_in = self._find_footer(buf, sig, i)
                    if end_in is not None:
                        end_pos = cur + end_in
                        data = buf[i:end_in]
                    else:
                        size_from = self._size_from_iso_bmff(buf, i, sig)
                        if size_from and i + size_from <= len(buf):
                            end_pos = cur + i + size_from
                            data = buf[i:i + size_from]

                    if not data:
                        read_more = 2 * self.chunk
                        try:
                            extra = self._read_at(global_pos, read_more)
                            if sig.footer:
                                j = extra.find(sig.footer, len(sig.header))
                                if j >= 0:
                                    data = extra[:j + len(sig.footer)]
                                else:
                                    data = extra
                            else:
                                data = extra
                            end_pos = global_pos + len(data)
                        except Exception:
                            data = buf[i:]
                            end_pos = cur + len(buf)

                    if len(data) < self.min_size:
                        start_index = i + 1
                        continue

                    if self.dedup:
                        from .utils import normalize_carve_data
                        canonical = normalize_carve_data(sig, data)
                        sha = self._sha256(canonical)
                        if sha in self._sha_seen:
                            start_index = i + 1
                            continue
                        self._sha_seen.add(sha)
                    ok = True
                    note = ""

                    out_name = f"{sig.name}_{global_pos}_len{len(data)}.{sig.ext}"
                    out_path, werr = self._write_file(sig.name, out_name, data)
                    if werr:
                        ok = False
                        note = werr
                    res = CarveResult(sig=sig, start=global_pos, end=end_pos or (global_pos + len(data)),
                                      out_path=out_path, ok=ok, note=note)
                    yield res
                    produced += 1
                    if self.max_files and produced >= self.max_files:
                        return
                    start_index = i + 1

            cur += len(buf) - overlap
            self._emit(cur)

        self._emit(self.total or cur)
