"""
Simple MFT record parser for OpenRecover.

This parser verifies the ``FILE`` signature and extracts a plausible
file name from a candidate record. It does not interpret attribute
runlists or timestamps; it only provides a heuristic placeholder.
"""

from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass
class ParsedRecord:
    record_number: int
    file_name: str
    size: int
    is_deleted: bool
    raw: bytes

class MFTParser:
    def __init__(self, record_size: int = 1024) -> None:
        self.record_size = record_size

    def parse(self, record: bytes, offset: int = 0) -> ParsedRecord:
        if len(record) < 4 or record[:4] != b'FILE':
            raise ValueError("Not an MFT record: missing FILE signature")
        rec_num = offset // self.record_size if self.record_size else 0
        name = ""
        ascii_pattern = re.compile(rb'[\x20-\x7e]{3,255}')
        for m in ascii_pattern.finditer(record):
            text = m.group().decode('latin1', errors='ignore')
            if '.' in text and not any(ch in '/\\:*?"<>|' for ch in text):
                name = text.strip()
                break
        return ParsedRecord(record_number=rec_num, file_name=name, size=0, is_deleted=False, raw=record)
