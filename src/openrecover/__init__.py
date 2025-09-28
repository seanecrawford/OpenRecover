"""
OpenRecover core package.

This package bundles together the scanning, parsing, carving and
recovery components of the OpenRecover toolkit. To avoid eager
importing of heavy dependencies (such as PySide6) the modules are
import-light. When adding new top-level exports be careful not to
import GUI frameworks here.
"""

# Re-export common classes for convenience
from .carver import FileCarver
from .scanner import NTFSScanner, MFTRecord
from .parser import MFTParser, ParsedRecord
from .recovery import FileRecovery

__all__ = [
    'FileCarver',
    'NTFSScanner',
    'MFTRecord',
    'MFTParser',
    'ParsedRecord',
    'FileRecovery',
]
