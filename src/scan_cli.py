import argparse, os
from openrecover.carver import FileCarver
from openrecover.signatures import ALL_SIGNATURES

def main():
    p = argparse.ArgumentParser(description="OpenRecover CLI")
    p.add_argument("--source", required=True, help="Path to image file or raw device (\\\\.\\E:)")
    p.add_argument("--out", required=True, help="Output folder")
    p.add_argument("--min-size", type=int, default=256)
    p.add_argument("--dedup", action="store_true")
    p.add_argument("--types", help="Comma-separated list of file types (e.g. jpg,png,pdf)", default="")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    types = [t.strip().lower() for t in args.types.split(",") if t.strip()]
    if types:
        from openrecover.signatures import ALL_SIGNATURES
        sig_map = {sig.name: sig for sig in ALL_SIGNATURES}
        sigs = [sig_map[t] for t in types if t in sig_map]
        if not sigs:
            print(f"No valid types specified; available types: {', '.join(sig_map.keys())}")
            return
    else:
        sigs = ALL_SIGNATURES
    c = FileCarver(args.source, args.out, sigs,
                   min_size=args.min_size, deduplicate=args.dedup,
                   progress_cb=lambda cur,total: print(f"{cur}/{total or '?'} bytes"))
    for r in c.scan():
        if r.ok:
            print(f"[hit] {r.sig.name} -> {r.out_path}")

if __name__ == "__main__":
    main()
