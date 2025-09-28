"""
Simple test runner for OpenRecover.
This script replicates a subset of pytest functionality to verify
the core FileCarver logic without requiring external dependencies.
"""
import os
import base64
import tempfile
import traceback
from openrecover.carver import FileCarver
from openrecover.signatures import PNG

def _create_sample_png() -> bytes:
    """Return bytes for a minimal 1x1 PNG image."""
    b64 = (
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/"
        b"x8AAwMB/6X6CtwAAAAASUVORK5CYII="
    )
    return base64.b64decode(b64)

def test_png_carver():
    sample_png = _create_sample_png()
    data = b"RANDOMDATA" + sample_png + b"TRAILER"
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "sample.bin")
        with open(src_file, "wb") as f:
            f.write(data)
        out_dir = os.path.join(tmp, "out")
        c = FileCarver(src_file, out_dir, [PNG], chunk=1024, overlap=128, min_size=0, deduplicate=True)
        results = list(c.scan())
        assert len(results) == 1, f"expected 1 result, got {len(results)}"
        res = results[0]
        assert res.ok, "carve result not ok"
        assert res.sig.name == "png", f"expected png sig, got {res.sig.name}"
        assert os.path.isfile(res.out_path), "output file not found"
        carved = open(res.out_path, "rb").read()
        assert carved.startswith(sample_png), "carved file does not match PNG signature"

def test_dedup():
    sample_png = _create_sample_png()
    data = sample_png + b"GAP" + sample_png
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "dup.bin")
        with open(src_file, "wb") as f:
            f.write(data)
        # deduplicate
        out_dir1 = os.path.join(tmp, "out1")
        c1 = FileCarver(src_file, out_dir1, [PNG], chunk=1024, overlap=0, min_size=0, deduplicate=True)
        results1 = list(c1.scan())
        assert len(results1) == 1, f"dedup true should return 1, got {len(results1)}"
        # no dedup
        out_dir2 = os.path.join(tmp, "out2")
        c2 = FileCarver(src_file, out_dir2, [PNG], chunk=1024, overlap=0, min_size=0, deduplicate=False)
        results2 = list(c2.scan())
        assert len(results2) == 2, f"dedup false should return 2, got {len(results2)}"

def run_all():
    """Run a subset of tests without requiring pytest.

    This function manually invokes a handful of test functions to
    verify the core OpenRecover logic. It is not exhaustive but
    provides quick feedback without pulling in the full pytest
    machinery. When adding new tests please import and append them
    here.
    """
    # Import additional tests lazily to avoid side effects
    from tests.test_scanner_parser_recovery import test_scanner_and_parser, test_recovery
    tests = [
        test_png_carver,
        test_dedup,
        test_scanner_and_parser,
        test_recovery,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"{t.__name__}: PASS")
        except Exception:
            failed += 1
            print(f"{t.__name__}: FAIL")
            traceback.print_exc()
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print("All tests passed")

if __name__ == "__main__":
    run_all()
