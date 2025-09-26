from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class FileSignature:
    name: str
    ext: str
    header: bytes
    footer: Optional[bytes] = None         # if None, size must be inferred
    header_adjust: int = 0                 # add/sub to where file content should begin
    size_from_header_iso_bmff: Optional[Tuple[int,int]] = None
    # (offset, size_len) for ISO BMFF (mp4/mov/avif/heif) box header size

# --- Core set (expand anytime) ---

JPEG = FileSignature(
    name="jpeg",
    ext="jpg",
    header=b"\xFF\xD8\xFF",
    footer=b"\xFF\xD9"
)

PNG = FileSignature(
    name="png",
    ext="png",
    header=b"\x89PNG\r\n\x1A\n",
    footer=b"IEND"   # we'll find the end of IEND chunk then add 8 bytes (len+type) + 4 CRC
)

GIF = FileSignature(
    name="gif",
    ext="gif",
    header=b"GIF8",
    footer=b"\x00\x3B",   # 0x3B is ';' terminator; keep simple
)

PDF = FileSignature(
    name="pdf",
    ext="pdf",
    header=b"%PDF-",
    footer=b"%%EOF"
)

WAV = FileSignature(
    name="wav",
    ext="wav",
    header=b"RIFF",
    footer=None
)

ZIP = FileSignature(
    name="zip",
    ext="zip",
    header=b"PK\x03\x04",
    footer=None
)

# ISO-BMFF group (mp4/mov/avif/heif)
# these containers start with a box that contains the total size in first 4 bytes.
MP4 = FileSignature(
    name="mp4",
    ext="mp4",
    header=b"\x00\x00\x00",        # size is first 4 bytes; we’ll treat specially
    footer=None,
    size_from_header_iso_bmff=(0, 4),
)
MOV = FileSignature(
    name="mov",
    ext="mov",
    header=b"\x00\x00\x00",
    footer=None,
    size_from_header_iso_bmff=(0, 4),
)
AVIF = FileSignature(
    name="avif",
    ext="avif",
    header=b"\x00\x00\x00",
    footer=None,
    size_from_header_iso_bmff=(0, 4),
)
HEIC = FileSignature(
    name="heic",
    ext="heic",
    header=b"\x00\x00\x00",
    footer=None,
    size_from_header_iso_bmff=(0, 4),
)

ALL_SIGNATURES = [
    JPEG, PNG, GIF, PDF, WAV, ZIP, MP4, MOV, AVIF, HEIC
]
