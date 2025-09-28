"""
Simple file recovery engine for OpenRecover.

The recovery component takes parsed MFT records and attempts to
reconstruct the corresponding file's data. A complete recovery
implementation would interpret the runlists of non-resident $DATA
attributes, handle resident attributes, alternate data streams and
fragmented extents. The current implementation is deliberately
minimal: it writes the raw bytes of the record to an output file.
This serves primarily as a placeholder and allows integration of the
API with the GUI and CLI while more advanced recovery logic is
developed.
"""

from __future__ import annotations

import os
from typing import Optional

from .parser import ParsedRecord
from .rawio import RawDevice
# No need to import private helpers. Directory creation is handled via os.makedirs.

class FileRecovery:
    """Recover files from parsed MFT records."""

    def __init__(self, source: str, output_dir: str, record_size: int = 1024) -> None:
        """Create a new recovery context.

        Parameters
        ----------
        source: str
            Path to the disk image or raw device.
        output_dir: str
            Directory where recovered files will be written.
        record_size: int, optional
            Size of each MFT record. Used to determine how much data
            to read when the $DATA runlist is unavailable. Defaults to
            1024 bytes.
        """
        self.source = source
        self.output_dir = output_dir
        self.record_size = record_size
        os.makedirs(self.output_dir, exist_ok=True)

    def recover(self, rec: ParsedRecord) -> str:
        """Recover a file from a parsed record.

        Since this minimal implementation does not parse runlists or
        non-resident attributes, it simply writes the raw MFT record
        bytes to disk. The filename is derived from the record's
        ``file_name`` field if present; otherwise a generic name is
        constructed from the record number.

        Parameters
        ----------
        rec: ParsedRecord
            Parsed MFT record.

        Returns
        -------
        str
            Path to the recovered file on disk.
        """
        # Determine output filename
        name = rec.file_name or f"record_{rec.record_number}.bin"
        # Replace characters that are illegal on Windows
        safe_name = ''.join(c if c not in '\\/:*?"<>|' else '_' for c in name)
        out_path = os.path.join(self.output_dir, safe_name)
        # Write the raw record bytes to disk
        with open(out_path, 'wb') as f:
            f.write(rec.raw)
        return out_path
