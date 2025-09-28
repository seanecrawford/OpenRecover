"""
Simple MFT record parser for OpenRecover.

The parser in this module is intentionally limited: it verifies the
``FILE`` signature and extracts a plausible file name from a
candidate record. It does not interpret attribute runlists or
timestamps and therefore cannot reconstruct complex metadata. The
primary goal of this parser is to provide a structured object that
downstream components (e.g., the recovery engine) can consume and
extend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedRecord:
    """Parsed representation of an MFT record.

    Attributes
    ----------
    record_number: int
        Ordinal number of the record, inferred from its offset by
        dividing by the record size (if known). If the record size
        cannot be determined this value is zero.
    file_name: str
        Best-effort extracted file name. For real MFT entries this
        comes from the $FILE_NAME attribute. If no plausible name is
        found this will be an empty string.
    size: int
        Reported file size. This parser always returns zero as it
        does not parse $DATA attributes. Downstream components must
        infer sizes from runlists if required.
    is_deleted: bool
        Indicates whether the record appears to be marked as
        deleted. The current implementation always returns False.
    raw: bytes
        Original bytes of the record for further analysis.
    """
    record_number: int
    file_name: str
    size: int
    is_deleted: bool
    raw: bytes

class MFTParser:
    """Parse candidate MFT records into structured representations."""

    def __init__(self, record_size: int = 1024) -> None:
        self.record_size = record_size

    def parse(self, record: bytes, offset: int = 0) -> ParsedRecord:
        """Parse a single MFT record.

        The parser checks for the standard ``FILE`` signature at the
        beginning of the record. It then performs a rudimentary scan
        through the record to find sequences of printable ASCII
        characters that look like filenames (i.e., containing a dot
        and no control characters). The first plausible filename is
        returned. Real MFT parsing involves traversing the attribute
        list and interpreting the $FILE_NAME attribute; this parser
        merely provides a heuristic placeholder.

        Parameters
        ----------
        record: bytes
            Raw bytes of the MFT record.
        offset: int, optional
            Byte offset of the record in the volume. Used to infer
            ``record_number`` when ``record_size`` is known.

        Returns
        -------
        ParsedRecord
        """
        if len(record) < 4 or record[:4] != b'FILE':
            raise ValueError("Not an MFT record: missing FILE signature")
        # Derive record number from offset if record_size non-zero
        rec_num = offset // self.record_size if self.record_size else 0
        name = ""
        # naive search for plausible filename
        # find ascii sequences between 3 and 255 chars containing a dot
        import re
        ascii_pattern = re.compile(rb'[\x20-\x7e]{3,255}')
        for m in ascii_pattern.finditer(record):
            text = m.group().decode('latin1', errors='ignore')
            if '.' in text and not any(ch in '/\\:*?"<>|' for ch in text):
                name = text.strip()
                break
        return ParsedRecord(record_number=rec_num, file_name=name, size=0, is_deleted=False, raw=record)
