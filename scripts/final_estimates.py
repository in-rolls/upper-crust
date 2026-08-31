#!/usr/bin/env python3
"""Merge dictionary matches with LLM adjudication into final estimates.

For each region and group:
  flagged     entities the dictionary matched
  confirmed   entities counted after adjudication (see veto policy below)
  p, ci       confirmed / n with a Wilson 95% CI

Veto policy: the LLM veto applies to the regional group only, where it judges
usage (branding vs incidental address text, e.g. "Domino's Pizza | JC Nagar,
Mysore") and performed well on inspection. For the caste groups the veto asked
a factual question the model gets wrong -- all 16 of its non-regional
rejections were real caste-linked surnames or communities (Kamat, Pai, Rao,
GSB, Marwadi), rejected with reasons like "kamat not a caste name" -- so there
the dictionary match stands, validated instead by manual inspection of every
distinct matched name.

The false-negative check: of the unmatched names sampled per region, the share
the LLM flagged as caste/community-coded AND confirmed on a targeted second
question. Reported per region as a rate with its own Wilson CI, plus a
corrected any-coded prevalence:
  p_corrected = confirmed_any/n + (unmatched/n) * fn_rate

Usage:
  python scripts/final_estimates.py --basepath data/analysis_2026_08_30 \
      --adjudication data/adjudication_2026_08_30.jsonl \
      --out data/final_estimates_2026_08_30.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import random
import re
from collections import defaultdict
from typing import Any, Dict, List

# Must mirror adjudicate_matches.py so the FN sample reproduces exactly.
FN_SAMPLE_PER_REGION = 500
SEED = 42


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def wilson_ci(k: int, n: int, z: float = 1.96):
    import math

    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def main() -> None:
    parser = argparse.ArgumentParser(description="Final adjudicated estimates")
    parser.add_argument("--basepath", required=True)
    parser.add_argument("--adjudication", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--fn-sample", type=int, default=FN_SAMPLE_PER_REGION)
    args = parser.parse_args()

    verdicts = read_jsonl(args.adjudication)
    genuine: Dict[str, bool] = {}
    screen: Dict[str, Dict[str, Any]] = {}
    verified_screen: Dict[str, bool] = {}
    for v in verdicts:
        if v["task"] == "verify_match":
            genuine[v["item_id"]] = v["verdict"].get("genuine") is True
        elif v["task"] == "screen_unmatched":
            screen[v["item_id"]] = v
        elif v["task"] == "verify_screen":
            verified_screen[v["item_id"]] = v["verdict"].get("genuine") is True

    out_rows = []
    fn_examples = []
    rng = random.Random(SEED)

    for path in sorted(glob.glob(f"{args.basepath}_region_*_matches.jsonl")):
        m = re.search(r"region_(\w+)_matches", path)
        region = m.group(1) if m else "unknown"
        rows = read_jsonl(path)
        n = len(rows)

        flagged_ids: Dict[str, set] = defaultdict(set)
        confirmed_ids: Dict[str, set] = defaultdict(set)
        unmatched = []
        missing_verdicts = 0
        for r in rows:
            if not r["matches"]:
                unmatched.append(r)
                continue
            for mt in r["matches"]:
                flagged_ids[mt["group"]].add(r["place_id"])
                key = f"A:{r['name_normalized']}:{mt['label']}"
                if key not in genuine:
                    missing_verdicts += 1
                elif mt["group"] != "regional" or genuine[key]:
                    confirmed_ids[mt["group"]].add(r["place_id"])
        if missing_verdicts:
            raise SystemExit(
                f"{region}: {missing_verdicts} flagged pairs have no "
                f"verdict — adjudication incomplete, re-run it first"
            )

        confirmed_any = set().union(*confirmed_ids.values()) if confirmed_ids else set()
        for group in sorted(flagged_ids):
            k_f, k_c = len(flagged_ids[group]), len(confirmed_ids[group])
            lo, hi = wilson_ci(k_c, n)
            out_rows.append(
                {
                    "region": region,
                    "group": group,
                    "n": n,
                    "flagged": k_f,
                    "confirmed": k_c,
                    "fp_rate": round(1 - k_c / k_f, 4) if k_f else "",
                    "p": f"{k_c / n:.6f}",
                    "ci_low": f"{lo:.6f}",
                    "ci_high": f"{hi:.6f}",
                }
            )

        # False-negative rate from the seeded sample of unmatched entities.
        sample = rng.sample(unmatched, min(args.fn_sample, len(unmatched)))
        fn_hits = 0
        for r in sample:
            s = screen.get(f"B:{r['name_normalized']}")
            if (
                s
                and s["verdict"].get("caste_coded") is True
                and verified_screen.get(f"C:{r['name_normalized']}", False)
            ):
                fn_hits += 1
                fn_examples.append((region, r["name"], s["verdict"].get("term", "")))
        fn_rate = fn_hits / len(sample) if sample else 0.0
        lo, hi = wilson_ci(fn_hits, len(sample))
        p_corr = len(confirmed_any) / n + (len(unmatched) / n) * fn_rate
        out_rows.append(
            {
                "region": region,
                "group": "fn_rate_sampled",
                "n": len(sample),
                "flagged": len(sample),
                "confirmed": fn_hits,
                "fp_rate": "",
                "p": f"{fn_rate:.6f}",
                "ci_low": f"{lo:.6f}",
                "ci_high": f"{hi:.6f}",
            }
        )
        out_rows.append(
            {
                "region": region,
                "group": "any_coded_corrected",
                "n": n,
                "flagged": "",
                "confirmed": len(confirmed_any),
                "fp_rate": "",
                "p": f"{p_corr:.6f}",
                "ci_low": "",
                "ci_high": "",
            }
        )
        print(
            f"{region}: n={n}, any confirmed {len(confirmed_any)} "
            f"({100 * len(confirmed_any) / n:.2f}%), FN {fn_hits}/{len(sample)} "
            f"({100 * fn_rate:.2f}%), corrected any-coded {100 * p_corr:.2f}%"
        )

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nwrote {args.out}")
    if fn_examples:
        print("\nNames the dictionary missed (confirmed by both LLM passes):")
        for region, name, term in fn_examples:
            print(f"  [{region}] {name}  ({term})")


if __name__ == "__main__":
    main()
