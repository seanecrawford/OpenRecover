import os
import tempfile
from openrecover.scanner import NTFSScanner
from openrecover.parser import MFTParser
from openrecover.recovery import FileRecovery
from openrecover.parser import ParsedRecord

def _create_mock_mft_record(record_size: int = 64) -> bytes:
    header = b'FILE' + b'\x00\x00\x00\x00'
    name = b'test.txt\x00'
    padding_len = max(0, record_size - len(header) - len(name))
    return header + name + (b'\x00' * padding_len)

def test_scanner_and_parser():
    record_size = 64
    rec_bytes = _create_mock_mft_record(record_size)
    data = b'RANDOM' + rec_bytes + b'JUNK'
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, 'image.bin')
        with open(src_path, 'wb') as f:
            f.write(data)
        scanner = NTFSScanner(record_size=record_size)
        records = list(scanner.scan_volume(src_path))
        assert len(records) == 1, f"expected 1 record, got {len(records)}"
        rec = records[0]
        assert rec.raw.startswith(b'FILE'), "record does not start with FILE signature"
        parser = MFTParser(record_size=record_size)
        parsed = parser.parse(rec.raw, offset=rec.offset)
        assert parsed.record_number == rec.offset // record_size
        assert parsed.file_name == 'test.txt', f"unexpected filename: {parsed.file_name}"
        assert parsed.raw == rec.raw

def test_recovery():
    raw = b'FILE\x00\x00\x00\x00hello world'
    parsed = ParsedRecord(record_number=0, file_name='hello.txt', size=0, is_deleted=False, raw=raw)
    with tempfile.TemporaryDirectory() as tmp:
        recov = FileRecovery(source=os.path.join(tmp, 'dummy.img'), output_dir=tmp)
        out_path = recov.recover(parsed)
        assert os.path.isfile(out_path), "recovered file not created"
        with open(out_path, 'rb') as f:
            assert f.read() == raw, "recovered data mismatch"
