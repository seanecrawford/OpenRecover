from dataclasses import dataclass
from typing import Optional, Callable, List, BinaryIO

@dataclass
class FileSignature:
    name: str
    extensions: List[str]
    header: bytes
    footer: Optional[bytes] = None
    max_size: int = 1024 * 1024 * 1024
    size_from_header: Optional[Callable[[BinaryIO,int], Optional[int]]] = None
    validate: Optional[Callable[[bytes], bool]] = None
    header_adjust: int = 0

# --- helpers ---
def _png_validate(b: bytes) -> bool:
    return b.endswith(b"\x00\x00\x00\x00IEND\xAE\x42\x60\x82")

def _ru32_be(f: BinaryIO, off: int) -> Optional[int]:
    f.seek(off); b=f.read(4); return int.from_bytes(b,"big") if len(b)==4 else None

def _ru64_be(f: BinaryIO, off: int) -> Optional[int]:
    f.seek(off); b=f.read(8); return int.from_bytes(b,"big") if len(b)==8 else None

# --- common parsers ---
def _iso_size(allowed: List[bytes], max_scan:int=4*1024*1024*1024):
    def fn(f:BinaryIO,start:int)->Optional[int]:
        s=_ru32_be(f,start); 
        if not s or s<8: return None
        f.seek(start+4); t=f.read(4)
        if t!=b"ftyp": return None
        major=f.read(4); ok=(len(major)==4 and major in allowed)
        rem=s-16 if s>=16 else 0
        if rem>0 and not ok:
            sm=f.read(min(rem,64))
            for i in range(0,len(sm),4):
                if sm[i:i+4] in allowed: ok=True; break
        if not ok: return None
        pos=start; limit=start+max_scan; last=None
        while pos+8<=limit:
            sz=_ru32_be(f,pos)
            if not sz: break
            f.seek(pos+4); f.read(4)
            if sz==0: return None
            if sz==1:
                ls=_ru64_be(f,pos+8); 
                if not ls or ls<16: return None
                np=pos+ls
            else:
                np=pos+sz
            if np<=pos or np-start>max_scan: break
            last=np; pos=np
        return (last-start) if last and last>start and (last-start)>=1024 else None
    return fn

def _riff_size(f,start,expect:bytes)->Optional[int]:
    f.seek(start); h=f.read(12)
    if len(h)<12: return None
    magic=h[:4]
    if magic==b"RIFF":
        sub=h[8:12]; size=int.from_bytes(h[4:8],"little")
    elif magic==b"FORM":
        sub=h[8:12]; size=int.from_bytes(h[4:8],"big")
    else: return None
    if sub!=expect: return None
    total=size+8
    return total if total>0 else None

def _riff_wav_size(f,start): return _riff_size(f,start,b"WAVE")

def _zip_eocd(f,start,max_scan=512*1024*1024)->Optional[int]:
    FOOT=b"PK\x05\x06"; CH=1024*1024
    try: f.seek(start+4)
    except Exception: return None
    scanned=0; tail=b""
    while scanned<max_scan:
        buf=f.read(CH)
        if not buf: break
        data=tail+buf; idx=data.find(FOOT)
        if idx!=-1:
            eocd=(start+4)+(len(tail)+idx)
            f.seek(eocd); e=f.read(22)
            if len(e)<22: return None
            cl=int.from_bytes(e[20:22],"little"); end=eocd+22+cl
            return end-start if end>start else None
        tail=data[-8:]; scanned+=len(buf)
    return None

# --- signatures ---
JPEG=FileSignature("jpeg",[".jpg",".jpeg"],b"\xFF\xD8\xFF",footer=b"\xFF\xD9",max_size=2*1024*1024*1024)
PNG =FileSignature("png",[".png"],b"\x89PNG\r\n\x1a\n",footer=b"\x00\x00\x00\x00IEND\xAE\x42\x60\x82",max_size=2*1024*1024*1024,validate=_png_validate)
PDF =FileSignature("pdf",[".pdf"],b"%PDF-",footer=b"%%EOF",max_size=2*1024*1024*1024)
ZIP =FileSignature("zip_or_office",[".zip",".docx",".xlsx",".pptx"],b"PK\x03\x04",size_from_header=_zip_eocd,max_size=2*1024*1024*1024)
WAV =FileSignature("wav",[".wav"],b"RIFF",size_from_header=_riff_wav_size,max_size=2*1024*1024*1024)
MP4 =FileSignature("mp4_mov",[".mp4",".mov",".m4v",".m4a",".3gp"],b"ftyp",header_adjust=4,size_from_header=_iso_size([b"isom",b"iso2",b"mp41",b"mp42",b"qt  ",b"M4V ",b"M4A ",b"3gp5",b"3g2a"],4*1024*1024*1024),max_size=4*1024*1024*1024)
HEIC=FileSignature("heic",[".heic",".heif",".avif"],b"ftyp",header_adjust=4,size_from_header=_iso_size([b"heic",b"heix",b"hevc",b"hevx",b"mif1",b"msf1",b"avif"],2*1024*1024*1024),max_size=2*1024*1024*1024)

# New: RAW camera, PST, SQLite
CR2 =FileSignature("cr2_raw",[".cr2"],b"\x49\x49\x2A\x00",max_size=512*1024*1024)
NEF =FileSignature("nef_raw",[".nef"],b"\x4D\x4D\x00\x2A",max_size=512*1024*1024)
ARW =FileSignature("arw_raw",[".arw"],b"\x49\x49\x2A\x00",max_size=512*1024*1024)
PST =FileSignature("pst",[".pst"],b"!\x42\x44\x4E",max_size=10*1024*1024*1024)
SQLITE=FileSignature("sqlite",[".db",".sqlite"],b"SQLite format 3\x00",max_size=4*1024*1024*1024)

ALL_SIGNATURES=[JPEG,PNG,PDF,ZIP,WAV,MP4,HEIC,CR2,NEF,ARW,PST,SQLITE]
