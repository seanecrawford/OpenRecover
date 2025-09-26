import os, sys, ctypes, mmap
from ctypes import wintypes
from typing import Optional

def to_raw_if_drive(path: str) -> str:
    """
    If the user gives 'E:', 'E:\\' or a folder on E:, return '\\\\.\\E:'.
    Otherwise return path unchanged.
    """
    p = (path or "").strip()
    if os.name == "nt":
        # Normalize like E:\something -> E:
        if len(p) >= 2 and p[1] == ":" and p[0].isalpha():
            drive = p[0].upper()
            return r"\\.\%s:" % drive
    return path

# ---------- Windows raw device ----------

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
    """
    Simple raw-device reader for Windows (e.g. '\\\\.\\E:').
    """
    def __init__(self, path: str, sector: int = 4096):
        self.path = path
        self.sector = sector
        self.handle = None
        self._open()

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
        # query size via IOCTL_DISK_GET_LENGTH_INFO
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

    def read_at(self, offset: int, size: int) -> bytes:
        # Move pointer
        SetFilePointerEx = ctypes.windll.kernel32.SetFilePointerEx
        SetFilePointerEx.argtypes = [
            wintypes.HANDLE, LARGE_INTEGER, ctypes.POINTER(LARGE_INTEGER), wintypes.DWORD
        ]
        SetFilePointerEx.restype = wintypes.BOOL

        newpos = LARGE_INTEGER(offset)
        ok = SetFilePointerEx(self.handle, newpos, None, 0)  # FILE_BEGIN=0
        if not ok:
            raise OSError("[SetFilePointerEx] failed at 0x%x" % offset)

        # Read
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

    def close(self):
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
