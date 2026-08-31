#!/usr/bin/env python3
"""Do SC/ST-informative surnames appear on restaurant signboards?

The dictionary measures branding by well-known caste and community terms,
which skew upper-caste and merchant. This check asks about the other end of
the hierarchy: surnames that are informative of Scheduled Caste or
Scheduled Tribe membership (from the SECC-weighted surname table built in
the last-name-basis repo). A surname qualifies when p_sc + p_st >= the
threshold and at least min-carriers people carry it in SECC 2011; matching
is the same word-boundary regex the main pipeline uses.

Usage:
  python scripts/scst_signal.py \
      --lookup ../last-name-basis/out/tab/per_name_secc_weighted.parquet \
      --inputs 'data/restaurants_2026_08_31_*_raw_collection.jsonl'
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_caste_branding import normalize_text  # noqa: E402


def main() -> None:
    import pandas as pd

    parser = argparse.ArgumentParser(description="SC/ST surname signal check")
    parser.add_argument("--lookup", required=True)
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--min-carriers", type=int, default=10000)
    args = parser.parse_args()

    d = pd.read_parquet(args.lookup)
    informative = d[
        ((d["p_sc"] + d["p_st"]) >= args.threshold) & (d["n"] >= args.min_carriers)
    ]["last_name"].tolist()
    # Very short tokens collide with ordinary words even at word boundaries.
    informative = [t for t in informative if len(t) >= 4]
    print(
        f"{len(informative)} SC/ST-informative surnames "
        f"(p_sc+p_st >= {args.threshold}, n >= {args.min_carriers}), e.g. "
        f"{', '.join(informative[:12])}"
    )

    pats = {
        t: re.compile(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])") for t in informative
    }

    files = []
    for p in args.inputs:
        files.extend(sorted(glob.glob(p)))
    for path in files:
        region = re.search(r"_([a-z0-9]+)_raw_collection", path).group(1)
        hits = defaultdict(list)
        n = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                n += 1
                norm = normalize_text(r["name"])
                for t, pat in pats.items():
                    if pat.search(norm):
                        hits[t].append(r["name"])
        total = sum(len(v) for v in hits.values())
        print(f"\n{region}: {total} of {n} names ({100 * total / n:.2f}%)")
        for t, names in sorted(hits.items()):
            for nm in names:
                print(f"  {t:12s} {nm}")


if __name__ == "__main__":
    main()
