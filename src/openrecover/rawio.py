import os, ctypes
from ctypes import wintypes
from typing import Optional

def to_raw_if_drive(path: str) -> str:
    p = (path or "").strip()
    if os.name == "nt":
        if len(p) >= 2 and p[1] == ":" and p[0].isalpha():
            drive = p[0].upper()
            return r"\\.\%s:" % drive
    return path

GENERIC_READ  = 0x80000000
OPEN_EXISTING = 3
FILE_SHARE_READ  = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_ATTRIBUTE_NORMAL = 0x00000080
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
IOCTL_DISK_GET_LENGTH_INFO = 0x0007405c

class LARGE_INTEGER(ctypes.Structure):
    _fields_ = [("QuadPart", ctypes.c_longlong)]

class RawDevice:
    def __init__(self, path: str, sector: int = 4096):
        self.path = path
        self.sector = sector
        if os.name == "nt":
            self.handle = None
            self._open()
            self.fd = None  # type: ignore
        else:
            self.fd = None  # type: Optional[int]
            self.handle = None  # type: ignore
            flags = os.O_RDONLY
            if hasattr(os, 'O_BINARY'):
                flags |= os.O_BINARY  # type: ignore
            try:
                self.fd = os.open(self.path, flags)
            except Exception as e:
                raise OSError(f"Failed to open raw device: {self.path}: {e}")

    def _open(self):
        CreateFileW = ctypes.windll.kernel32.CreateFileW
        CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
        ]
        CreateFileW.restype = wintypes.HANDLE
        handle = CreateFileW(
            self.path,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None
        )
        if handle == INVALID_HANDLE_VALUE or handle is None:
            raise OSError("Failed to open raw device: %s" % self.path)
        self.handle = handle

    @property
    def length(self) -> Optional[int]:
        if os.name == "nt":
            out = LARGE_INTEGER()
            bytes_ret = wintypes.DWORD(0)
            ok = ctypes.windll.kernel32.DeviceIoControl(
                self.handle,
                IOCTL_DISK_GET_LENGTH_INFO,
                None, 0,
                ctypes.byref(out), ctypes.sizeof(out),
                ctypes.byref(bytes_ret),
                None
            )
            return int(out.QuadPart) if ok else None
        else:
            try:
                st = os.stat(self.path)
                return st.st_size
            except Exception:
                return None

    def read_at(self, offset: int, size: int) -> bytes:
        if os.name == "nt":
            SetFilePointerEx = ctypes.windll.kernel32.SetFilePointerEx
            SetFilePointerEx.argtypes = [
                wintypes.HANDLE, LARGE_INTEGER, ctypes.POINTER(LARGE_INTEGER), wintypes.DWORD
            ]
            SetFilePointerEx.restype = wintypes.BOOL
            newpos = LARGE_INTEGER(offset)
            ok = SetFilePointerEx(self.handle, newpos, None, 0)
            if not ok:
                raise OSError("[SetFilePointerEx] failed at 0x%x" % offset)
            ReadFile = ctypes.windll.kernel32.ReadFile
            ReadFile.argtypes = [
                wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID
            ]
            ReadFile.restype = wintypes.BOOL
            buf = (ctypes.c_ubyte * size)()
            read = wintypes.DWORD(0)
            ok = ReadFile(self.handle, ctypes.byref(buf), size, ctypes.byref(read), None)
            if not ok:
                raise OSError("[ReadFile] failed at 0x%x" % offset)
            return bytes(buf[:read.value])
        else:
            if hasattr(os, 'pread') and self.fd is not None:
                try:
                    return os.pread(self.fd, size, offset)
                except Exception as e:
                    raise OSError(f"pread failed at 0x{offset:x}: {e}")
            with os.fdopen(os.dup(self.fd), 'rb', closefd=True) as f:
                f.seek(offset)
                return f.read(size)

    def close(self):
        if os.name == "nt":
            if getattr(self, 'handle', None):
                ctypes.windll.kernel32.CloseHandle(self.handle)
                self.handle = None
        else:
            if getattr(self, 'fd', None) is not None:
                os.close(self.fd)
                self.fd = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
