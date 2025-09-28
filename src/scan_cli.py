import argparse, os
from openrecover.carver import FileCarver
from openrecover.signatures import ALL_SIGNATURES

def main():
    p=argparse.ArgumentParser(description="OpenRecover CLI")
    p.add_argument("--source",required=True,help="Path to image file or raw device (\\\\.\\E:)")
    p.add_argument("--out",required=True,help="Output folder")
    p.add_argument("--min-size",type=int,default=256)
    p.add_argument("--dedup",action="store_true")
    args=p.parse_args()
    os.makedirs(args.out,exist_ok=True)
    c=FileCarver(args.source,args.out,ALL_SIGNATURES,min_size=args.min_size,deduplicate=args.dedup,
                 progress_cb=lambda cur,total: print(f"{cur}/{total or '?'} bytes"))
    # Note: original code referenced 'hit_cb', which doesn't exist. Use scan results instead.
    for r in c.scan():
        if r.ok:
            print(f"[hit] {r.sig.name} -> {r.out_path}")

if __name__=="__main__":
    main()
