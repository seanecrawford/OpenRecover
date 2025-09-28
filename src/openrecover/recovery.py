"""
Simple file recovery engine for OpenRecover.

This minimal recovery implementation writes the raw MFT record bytes
to an output file.  It does not interpret runlists, alternate data
streams or non-resident attributes.
"""

from __future__ import annotations
import os
from .parser import ParsedRecord

class FileRecovery:
    def __init__(self, source: str, output_dir: str, record_size: int = 1024) -> None:
        self.source = source
        self.output_dir = output_dir
        self.record_size = record_size
        os.makedirs(self.output_dir, exist_ok=True)

    def recover(self, rec: ParsedRecord) -> str:
        name = rec.file_name or f"record_{rec.record_number}.bin"
        safe_name = ''.join(c if c not in '\\/:*?"<>|' else '_' for c in name)
        out_path = os.path.join(self.output_dir, safe_name)
        with open(out_path, 'wb') as f:
            f.write(rec.raw)
        return out_path
