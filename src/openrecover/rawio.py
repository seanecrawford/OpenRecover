
import os, ctypes
from ctypes import wintypes
ERROR_INVALID_PARAMETER=87; ERROR_IO_DEVICE=1117; ERROR_CRC=23
GENERIC_READ=0x80000000; FILE_SHARE_READ=1; FILE_SHARE_WRITE=2; OPEN_EXISTING=3; FILE_ATTRIBUTE_NORMAL=0x80
FILE_BEGIN,FILE_CURRENT,FILE_END=0,1,2; IOCTL_DISK_GET_LENGTH_INFO=0x0007405C
CreateFileW=ctypes.windll.kernel32.CreateFileW; ReadFile=ctypes.windll.kernel32.ReadFile
SetFilePointerEx=ctypes.windll.kernel32.SetFilePointerEx; CloseHandle=ctypes.windll.kernel32.CloseHandle
DeviceIoControl=ctypes.windll.kernel32.DeviceIoControl; GetLastError=ctypes.windll.kernel32.GetLastError
class RawError(OSError): pass
class RawDevice:
    def __init__(self, path:str, sector_size:int=4096):
        if os.name!="nt": raise RawError(0,"Windows only")
        self.path=path; self.sector=sector_size
        h=CreateFileW(ctypes.c_wchar_p(path), GENERIC_READ, FILE_SHARE_READ|FILE_SHARE_WRITE, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
        if h in (ctypes.c_void_p(-1).value, 0): raise RawError(GetLastError(),"CreateFileW failed")
        self.handle=h; self.length=self._len()
    def _len(self)->int:
        class LI(ctypes.Structure): _fields_=[("QuadPart", ctypes.c_longlong)]
        out=LI(); ret=wintypes.DWORD()
        ok=DeviceIoControl(self.handle, IOCTL_DISK_GET_LENGTH_INFO, None,0, ctypes.byref(out), ctypes.sizeof(out), ctypes.byref(ret), None)
        return int(out.QuadPart) if ok else 0
    def seek(self, off:int, whence:int=FILE_BEGIN)->bool:
        newp=ctypes.c_longlong(); return bool(SetFilePointerEx(self.handle, ctypes.c_longlong(off), ctypes.byref(newp), whence))
    def _read_once(self, n:int)->bytes:
        buf=ctypes.create_string_buffer(n); got=wintypes.DWORD()
        ok=ReadFile(self.handle, buf, n, ctypes.byref(got), None)
        if not ok:
            err=GetLastError()
            if err in (ERROR_INVALID_PARAMETER, ERROR_IO_DEVICE, ERROR_CRC): raise RawError(err,"ReadFile failed")
            raise RawError(err,"ReadFile unexpected error")
        return buf.raw[:got.value]
    def read_at(self, offset:int, size:int)->bytes:
        align=self.sector; base=(offset//align)*align; front=offset-base; need=size+front
        if self.length: need=min(need, max(0, self.length-base))
        for chunk in (1024*1024, 256*1024, 64*1024, 4096):
            pos=base; remain=need; parts=[]; ok=True
            while remain>0:
                sz=min(chunk,remain)
                if not self.seek(pos, FILE_BEGIN): ok=False; break
                try: data=self._read_once(sz)
                except RawError: ok=False; break
                if not data: ok=False; break
                parts.append(data); pos+=len(data); remain-=len(data)
            if ok:
                blob=b"".join(parts); return blob[front:front+size]
        raise RawError(ERROR_INVALID_PARAMETER, f"read_at failed at {offset}")
    def close(self):
        if getattr(self,"handle",None): CloseHandle(self.handle); self.handle=None
    def __enter__(self): return self
    def __exit__(self,a,b,c): self.close()
def to_raw_if_drive(path:str)->str:
    drive,_=os.path.splitdrive(path)
    if drive:
        letter=drive.replace(":","").strip()
        if len(letter)==1 and letter.isalpha(): return r"\\.\%s:"%letter.upper()
    return path
