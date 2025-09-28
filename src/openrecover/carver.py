import os, hashlib
from dataclasses import dataclass
from typing import List, Callable, Optional, Iterable, Dict, Tuple
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
    # Windows long path prefix
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
        chunk: int = 16*1024*1024,
        overlap: int = 256*1024,
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

        # Decide reader
        sp = to_raw_if_drive(self.src_str)
        self._is_raw = (sp.startswith(r"\\.\\".rstrip("\\")) and os.name=="nt")
        self._raw = RawDevice(sp) if self._is_raw else None
        self._fin = None
        if not self._is_raw:
            self._fin = open(sp, "rb", buffering=0)

        # size
        if self._is_raw:
            self.total = self._raw.length or 0
        else:
            self.total = os.path.getsize(sp)

        # cut by max_bytes
        if self.max_bytes and self.total:
            self.total = min(self.total, self.max_bytes)

        _ensure_dir(self.output_dir)

    def close(self):
        if self._raw:
            self._raw.close()
        if self._fin:
            self._fin.close()

    # ---- low-level read ----
    def _read_at(self, off: int, size: int) -> bytes:
        if self._is_raw:
            return self._raw.read_at(off, size)
        else:
            self._fin.seek(off, os.SEEK_SET)
            return self._fin.read(size)

    # ---- carving helpers ----
    def _emit(self, cur: int):
        self.progress_cb(cur, self.total or 0)

    def _sha256(self, data: bytes) -> str:
        """Return a SHA‑256 hex digest.

        This wrapper delegates to the ``utils.sha256`` function so
        hashing logic can be centralised and easily patched in tests.
        """
        from .utils import sha256 as _sha
        return _sha(data)

    def _write_file(self, subdir: str, name: str, data: bytes) -> Tuple[str, Optional[str]]:
        out_dir = os.path.join(self.output_dir, subdir)
        _ensure_dir(out_dir)
        # prevent too long names
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
        # Special case PNG: include entire IEND chunk (12 bytes).
        # When locating the footer for a PNG we want to include the 4-byte
        # ``IEND`` marker and its 4-byte CRC. The 4-byte length field
        # preceding ``IEND`` is already part of the data slice as it
        # comes before ``IEND``. Therefore we add ``len(sig.footer)``
        # (4 bytes) plus 4 additional bytes for the CRC.
        if sig is not None and sig.name == "png":
            return idx + len(sig.footer) + 4
        # Generic: include the footer bytes
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

    # ---- main scan generator ----
    def scan(self) -> Iterable[CarveResult]:
        cur = self.start_offset
        produced = 0
        overlap = min(self.overlap, self.chunk//2)

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
            except Exception as e:
                # move forward by a sector to avoid infinite loop on bad zones
                cur += 4096
                self._emit(cur)
                continue

            if not buf:
                break

            # search signatures
            for sig in self.signatures:
                start_index = 0
                while True:
                    i = buf.find(sig.header, start_index)
                    if i < 0:
                        break
                    global_pos = cur + i

                    # Try to compute length
                    data = b""
                    end_pos = None
                    # try footer in this chunk
                    end_in = self._find_footer(buf, sig, i)
                    if end_in is not None:
                        end_pos = cur + end_in
                        data = buf[i:end_in]
                    else:
                        # ISO BMFF size from header if possible
                        size_from = self._size_from_iso_bmff(buf, i, sig)
                        if size_from and i + size_from <= len(buf):
                            end_pos = cur + i + size_from
                            data = buf[i:i+size_from]

                    # If still unknown, read a conservative window externally
                    if not data:
                        # read an extra window
                        read_more = 2 * self.chunk
                        try:
                            extra = self._read_at(global_pos, read_more)
                            # footer search there
                            if sig.footer:
                                j = extra.find(sig.footer, len(sig.header))
                                if j >= 0:
                                    data = extra[:j + len(sig.footer)]
                                else:
                                    data = extra  # best-effort
                            else:
                                data = extra  # best-effort
                            end_pos = global_pos + len(data)
                        except Exception as e:
                            data = buf[i:]
                            end_pos = cur + len(buf)

                    # sanity size
                    if len(data) < self.min_size:
                        start_index = i + 1
                        continue

                    # dedup: normalise data to canonical slice for hashing
                    if self.dedup:
                        from .utils import normalize_carve_data
                        canonical = normalize_carve_data(sig, data)
                        sha = self._sha256(canonical)
                        if sha in self._sha_seen:
                            # Skip duplicate files entirely
                            start_index = i + 1
                            continue
                        self._sha_seen.add(sha)
                    ok = True
                    note = ""

                    # write file
                    out_name = f"{sig.name}_{global_pos}_len{len(data)}.{sig.ext}"
                    out_path, werr = self._write_file(sig.name, out_name, data)
                    if werr:
                        ok = False
                        note = werr

                    res = CarveResult(sig=sig, start=global_pos, end=end_pos or (global_pos+len(data)),
                                      out_path=out_path, ok=ok, note=note)
                    yield res
                    produced += 1
                    if self.max_files and produced >= self.max_files:
                        return
                    start_index = i + 1

            # advance
            cur += len(buf) - overlap
            self._emit(cur)

        # done
        self._emit(self.total or cur)
