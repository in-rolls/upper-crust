#!/usr/bin/env python3
"""Reconstruct raw collection JSONL files from analysis matches files.

The original raw collections for Bengaluru (blr) and Mysuru (mys) were never
committed; only Chennai's (maa) survives. The committed matches files retain
every raw field plus a ``matches`` key, so dropping that key recovers the raw
rows. Caveat: matches files hold the *deduped* rows (the analyzer deduped on
(place_id, normalized name) before matching), so exact duplicate rows from the
original collection are unrecoverable. The maa round-trip below shows whether
that matters in practice.

Usage:
  python scripts/reconstruct_raw.py
"""

import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
STAMP = "2025_08_22"


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def reconstruct(region):
    rows = read_jsonl(DATA / f"analysis_{STAMP}_region_{region}_matches.jsonl")
    out = []
    for r in rows:
        r = dict(r)
        r.pop("matches", None)
        out.append(r)
    return out


def row_multiset(rows):
    return Counter(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)


def main():
    # Verify the method on maa, where the true raw file survives.
    truth = row_multiset(
        read_jsonl(DATA / f"restaurants_{STAMP}_maa_raw_collection.jsonl")
    )
    rebuilt = row_multiset(reconstruct("maa"))
    if truth != rebuilt:
        only_truth = truth - rebuilt
        only_rebuilt = rebuilt - truth
        raise SystemExit(
            f"maa round-trip FAILED: {sum(only_truth.values())} rows only in raw, "
            f"{sum(only_rebuilt.values())} only in reconstruction"
        )
    print(f"maa round-trip OK: {sum(truth.values())} rows identical")

    for region in ("blr", "mys"):
        out_path = DATA / f"restaurants_{STAMP}_{region}_raw_collection.jsonl"
        rows = reconstruct(region)
        with open(out_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {out_path.name}: {len(rows)} rows (reconstructed from matches)")


if __name__ == "__main__":
    main()
