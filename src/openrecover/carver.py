import os, hashlib, re
from typing import List, Optional, Set
from .signatures import FileSignature, ALL_SIGNATURES
from .rawio import RawDevice, to_raw_if_drive

class CarveResult:
    def __init__(self,start:int,end:int,sig:FileSignature,out_path:str,sha256:str,ok:bool,note:str=""):
        self.start=start; self.end=end; self.sig=sig
        self.out_path=out_path; self.sha256=sha256
        self.ok=ok; self.note=note

# helper: sanitize filenames for Windows/Linux
def _safe_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_.@-]', '_', s)

class Reader:
    def __init__(self, source:str):
        p=to_raw_if_drive(source)
        self.length=0
        if os.name=="nt" and p.startswith(r"\\.\\" ):
            self.dev=RawDevice(p,4096); self._pos=0; self.length=self.dev.length or 0
        else:
            self.f=open(p,"rb",buffering=0); self._pos=0
            try: self.f.seek(0,os.SEEK_END); self.length=self.f.tell(); self.f.seek(0)
            except Exception: self.length=0

    def read(self,n:int)->bytes:
        if hasattr(self,"dev"):
            try: b=self.dev.read_at(self._pos,n)
            except Exception: b=b""
            self._pos+=len(b); return b
        else:
            b=self.f.read(n); self._pos+=len(b); return b

    def seek(self,off:int,whence:int=os.SEEK_SET)->bool:
        try:
            if hasattr(self,"dev"):
                if whence==os.SEEK_SET: self._pos=off
                elif whence==os.SEEK_CUR: self._pos+=off
                elif whence==os.SEEK_END: self._pos=self.length or self._pos
                return True
            else:
                self.f.seek(off,whence); self._pos=self.f.tell(); return True
        except Exception: return False

    def close(self):
        if hasattr(self,"dev"): self.dev.close()
        if hasattr(self,"f"): self.f.close()

class FileCarver:
    def __init__(self, source_path:str, output_dir:str, signatures:List[FileSignature]=None,
                 chunk:int=16*1024*1024, overlap:int=256*1024, max_files:int=0,
                 fast_index:bool=False, max_bytes:int=0, min_size:int=256, 
                 progress_cb=None, deduplicate:bool=True):
        self.source_path=source_path; self.output_dir=output_dir; self.sigs=signatures or ALL_SIGNATURES
        self.chunk=max(1024*1024,chunk); self.ov=max(4096,overlap)
        self.max_files=max_files; self.fast_index=fast_index
        self.max_bytes=max_bytes; self.min_size=min_size
        self.progress_cb=progress_cb; self.dedup=deduplicate; self._hashes:Set[str]=set()
        self.hit_cb=None
        os.makedirs(self.output_dir,exist_ok=True)

    def _out(self,sig,start,length)->str:
        d=os.path.join(self.output_dir,sig.name)
        os.makedirs(d,exist_ok=True)
        fname=_safe_name(f"{sig.name}_@{start}_len{length}{sig.extensions[0]}")
        return os.path.join(d,fname)

    def _stream(self,r,start,total,outp):
        r.seek(start); remain=total; h=hashlib.sha256()
        try:
            with open(outp,"wb") as w:
                while remain>0:
                    b=r.read(min(1024*1024,remain))  # smaller increments
                    if not b: return False,"","truncated"
                    w.write(b); h.update(b); remain-=len(b)
                    # smoother progress callback
                    if self.progress_cb:
                        self.progress_cb(r._pos, getattr(r,"length",0))
        except Exception as e:
            return False,"",f"write error: {e}"
        return True,h.hexdigest(),""

    def _from_hdr(self,r,hdr,sig):
        start=hdr - sig.header_adjust
        if start<0: return None
        size=None
        if sig.size_from_header:
            try: size=sig.size_from_header(r,start)
            except Exception: size=None
        if size is None or size<self.min_size or size>sig.max_size: return None
        outp=self._out(sig,start,size)
        if self.fast_index: return CarveResult(start,start+size,sig,outp,"",True,"indexed")
        ok,sha,note=self._stream(r,start,size,outp)
        if ok and self.dedup:
            if sha in self._hashes: 
                try: os.remove(outp)
                except Exception: pass
                return CarveResult(start,start+size,sig,outp,sha,False,"duplicate skipped")
            self._hashes.add(sha)
        return CarveResult(start,start+size,sig,outp,sha,ok,note)

    def scan(self):
        r=Reader(self.source_path)
        try:
            total=getattr(r,"length",0) or 0; abs_off=0; tail=b""
            while True:
                if self.max_files and len(self._hashes)>=self.max_files: break
                if self.max_bytes and abs_off>=self.max_bytes: break
                buf=r.read(self.chunk)
                if not buf: break
                data=tail+buf
                for sig in self.sigs:
                    i=0
                    while True:
                        idx=data.find(sig.header,i)
                        if idx==-1: break
                        r2=self._from_hdr(r, abs_off - len(tail) + idx, sig)
                        if r2 and self.hit_cb: self.hit_cb(r2)
                        i=idx+1
                tail=data[-min(self.ov,len(data)):]
                abs_off+=len(buf)
                if self.progress_cb: self.progress_cb(abs_off,total)
        finally:
            r.close()
