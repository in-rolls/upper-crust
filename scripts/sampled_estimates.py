#!/usr/bin/env python3
"""Prevalence estimates for the sampled (points-based) collections.

Units are restaurants captured by randomly sampled street-segment circles.
Sampled points are the clusters, so CIs come from a cluster bootstrap over
points (resampling points with replacement, B draws, percentile intervals).
Two estimators:
  unweighted   share of captured restaurants whose name is coded
  weighted     the same with weight 1 / local frame density at the capturing
               point (restaurants in street-dense areas are more likely to be
               captured; density is frame_segments_within_radius from the
               sample CSV)

Adjudication verdicts apply as in final_estimates.py: the LLM veto counts
for the regional group only.

Usage:
  python scripts/sampled_estimates.py \
      --matches data/analysis_X_region_maa2_matches.jsonl \
      --adjudication data/adjudication_2026_08_30.jsonl \
      --sample-csv data/sampling/chennai_segments_n400_seed42.csv \
      --out data/sampled_estimates_maa2.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from typing import Any, Dict, List

B = 2000
SEED = 7


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sampled-collection estimates")
    parser.add_argument("--matches", required=True)
    parser.add_argument("--adjudication", required=True)
    parser.add_argument("--sample-csv", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    genuine = {}
    for v in read_jsonl(args.adjudication):
        if v["task"] == "verify_match":
            genuine[v["item_id"]] = v["verdict"].get("genuine") is True

    # Point order in the sample CSV = cell_idx order used by the collector
    # (both read the CSV top to bottom), so row i's density belongs to
    # cell_idx i.
    density = {}
    with open(args.sample_csv, encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            density[i] = max(1, int(row["frame_segments_within_radius"]))

    rows = read_jsonl(args.matches)
    by_point: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    missing = 0
    for r in rows:
        coded_groups = set()
        for mt in r["matches"]:
            key = f"A:{r['name_normalized']}:{mt['label']}"
            if key not in genuine:
                missing += 1
            elif mt["group"] != "regional" or genuine[key]:
                coded_groups.add(mt["group"])
        r["_coded_groups"] = coded_groups
        by_point[r.get("cell_idx", -1)].append(r)
    if missing:
        raise SystemExit(f"{missing} flagged pairs lack verdicts; adjudicate first")

    points = sorted(by_point)
    groups = sorted({g for r in rows for g in r["_coded_groups"]} | {"any"})

    def estimates(point_list):
        num_u = defaultdict(float)
        num_w = defaultdict(float)
        den_u = den_w = 0.0
        for p in point_list:
            w = 1.0 / density.get(p, 1)
            for r in by_point[p]:
                den_u += 1
                den_w += w
                for g in r["_coded_groups"]:
                    num_u[g] += 1
                    num_w[g] += w
                if r["_coded_groups"]:
                    num_u["any"] += 1
                    num_w["any"] += w
        return (
            {g: num_u[g] / den_u if den_u else 0.0 for g in groups},
            {g: num_w[g] / den_w if den_w else 0.0 for g in groups},
        )

    point_est_u, point_est_w = estimates(points)
    rng = random.Random(SEED)
    boots_u = defaultdict(list)
    boots_w = defaultdict(list)
    for _ in range(B):
        draw = [rng.choice(points) for _ in points]
        eu, ew = estimates(draw)
        for g in groups:
            boots_u[g].append(eu[g])
            boots_w[g].append(ew[g])

    def pct(xs, q):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(q * len(xs)))]

    n = sum(len(v) for v in by_point.values())
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            [
                "group",
                "n",
                "n_points",
                "p_unweighted",
                "ci_low",
                "ci_high",
                "p_weighted",
                "w_ci_low",
                "w_ci_high",
            ]
        )
        for g in groups:
            w.writerow(
                [
                    g,
                    n,
                    len(points),
                    f"{point_est_u[g]:.6f}",
                    f"{pct(boots_u[g], 0.025):.6f}",
                    f"{pct(boots_u[g], 0.975):.6f}",
                    f"{point_est_w[g]:.6f}",
                    f"{pct(boots_w[g], 0.025):.6f}",
                    f"{pct(boots_w[g], 0.975):.6f}",
                ]
            )
            print(
                f"{g:20s} unweighted {100 * point_est_u[g]:5.2f}% "
                f"[{100 * pct(boots_u[g], 0.025):.2f}, {100 * pct(boots_u[g], 0.975):.2f}]  "
                f"weighted {100 * point_est_w[g]:5.2f}% "
                f"[{100 * pct(boots_w[g], 0.025):.2f}, {100 * pct(boots_w[g], 0.975):.2f}]"
            )
    print(f"n={n} restaurants across {len(points)} points -> {args.out}")


if __name__ == "__main__":
    main()
