"""Batch ingest tickers by calling src/ingest_companyfacts.py with SEC_TICKERS set.
Usage: python tools\batch_ingest.py --file data/tickers.txt --batch 25 --pause 3
"""
import argparse
import os
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--file", default="data/tickers.txt")
parser.add_argument("--batch", type=int, default=25)
parser.add_argument("--pause", type=float, default=3.0)
args = parser.parse_args()

if not os.path.exists(args.file):
    print("Tickers file not found:", args.file)
    raise SystemExit(1)

with open(args.file) as f:
    tickers = [line.strip().upper() for line in f if line.strip()]

n = len(tickers)
print(f"Found {n} tickers; batch size {args.batch}")

for i in range(0, n, args.batch):
    batch = tickers[i : i + args.batch]
    env = os.environ.copy()
    env["SEC_TICKERS"] = ",".join(batch)
    print(f"Running batch {i//args.batch+1}: {len(batch)} tickers ({batch[0]} ... {batch[-1]})")
    # run ingest script from repo root
    proc = subprocess.run(["python", "src/ingest_companyfacts.py"], env=env, cwd=os.path.dirname(os.path.dirname(__file__)))
    if proc.returncode != 0:
        print(f"Ingest script failed for batch starting at index {i} (exit {proc.returncode})")
        # don't abort; continue to next batch
    time.sleep(args.pause)

print("Batch ingestion finished.")