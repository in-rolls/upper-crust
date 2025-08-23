#!/usr/bin/env python3
"""
Analyzer — Caste/Community-coded Branding from Raw Restaurant Catalogs
----------------------------------------------------------------------

Purpose
  Load one or more raw catalogs (JSONL) produced by the collector and estimate
  how common caste/community-coded *names* are. Denominators can be based on:
    • observed union per region, or
    • capture–recapture (Chapman) if both Places and OSM present with overlap.

Outputs
  For each region and for the combined dataset:
    • <base>_<scope>_summary.json
    • <base>_<scope>_matches.jsonl
    • <base>_<scope>_group_prevalence.csv
    • <base>_<scope>_label_counts.csv

Notebook-friendly
  • Use analyze_run_notebook(files=[...], group_by_region=True, ...)

Notes
  • Name-based markers are a proxy; interpret with care. We report groups
    separately (e.g., upper_caste vs surname_title).
  • Fuzzy matching is conservative (token-level Levenshtein; phrases use regex).
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ----------------------------- Normalization --------------------------------

def normalize_text(s: str) -> str:
    s0 = unicodedata.normalize("NFKC", s or "")
    s1 = "".join(c for c in unicodedata.normalize("NFD", s0) if not unicodedata.combining(c))
    s2 = re.sub(r"\s+", " ", s1).strip().lower()
    return s2

def tokenize_simple(s: str) -> List[str]:
    s = normalize_text(s)
    tokens = re.split(r"[^a-z0-9']+", s)
    return [t for t in tokens if t]

def levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            cur = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = cur
    return dp[m]

# ------------------------------- Statistics ---------------------------------

def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + (z ** 2) / n
    center = (p + (z ** 2) / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p)) / n + (z ** 2) / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))

# Capture–recapture (Chapman)

def capture_recapture(A: int, B: int, m: int, z: float = 1.96) -> Dict[str, float]:
    if A <= 0 or B <= 0 or m <= 0:
        return {"N_hat": float("nan"), "se": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    N_hat = ((A + 1) * (B + 1) / (m + 1)) - 1
    var = ((A + 1) * (B + 1) * (A - m) * (B - m)) / (((m + 1) ** 2) * (m + 2))
    se = math.sqrt(max(var, 0.0))
    ci_low = max(0.0, N_hat - z * se)
    ci_high = N_hat + z * se
    return {"N_hat": N_hat, "se": se, "ci_low": ci_low, "ci_high": ci_high}

# ------------------------------ Transliteration -----------------------------

def _expand_variants_base(term: str):
    base = term.strip().lower()
    yield base; yield base + "'s"; yield base + ("s" if not base.endswith("s") else "")

def _apply_substitutions_once(s: str):
    subs = [(r"^ai","i"),(r"^i","ai"),(r"w","v"),(r"bhawan","bhavan"),(r"bhavan","bhawan"),(r"sh","s"),(r"yy","y"),(r"oo","u")]
    yielded = {s}
    for pat, repl in subs:
        candidate = re.sub(pat, repl, s)
        if candidate != s:
            yielded.add(candidate)
    return yielded

def translit_variants(term: str) -> List[str]:
    base_set = set(_expand_variants_base(term))
    expanded = set()
    for b in base_set:
        expanded.add(b)
        for c in _apply_substitutions_once(b):
            expanded.add(c)
    out = set()
    for v in expanded:
        v2 = re.sub(r"(.)\1", r"\1", v)
        out.add(v); out.add(v2)
    return sorted(out)

# -------------------------------- Taxonomy ----------------------------------

def taxonomy() -> List[Dict[str, Any]]:
    cats: List[Dict[str, Any]] = []
    # Upper-caste
    cats += [
        {"label": "Brahmin (general)", "group": "upper_caste", "terms": ["brahmin"]},
        {"label": "Iyengar (Tamil Brahmin)", "group": "upper_caste", "terms": ["iyengar","mandyam"]},
        {"label": "Iyer (Tamil Brahmin)", "group": "upper_caste", "terms": ["iyer"]},
        {"label": "Madhva / Dvaita (Brahmin)", "group": "upper_caste", "terms": ["madhva","madhwa"]},
        {"label": "Smartha (Brahmin)", "group": "upper_caste", "terms": ["smartha"]},
        {"label": "Deshastha (Brahmin)", "group": "upper_caste", "terms": ["deshastha"]},
        {"label": "Gaud Saraswat / GSB", "group": "upper_caste", "terms": ["saraswat","saraswath","gaud saraswat","gsb"]},
        {"label": "Havyaka (Brahmin)", "group": "upper_caste", "terms": ["havyaka"]},
        {"label": "Shivalli (Brahmin)", "group": "upper_caste", "terms": ["shivalli"]},
        {"label": "Hebbar (Brahmin - ambiguous)", "group": "upper_caste", "terms": ["hebbar"]},
    ]
    # Merchant
    cats += [
        {"label": "Jain", "group": "merchant_community", "terms": ["jain"]},
        {"label": "Marwari", "group": "merchant_community", "terms": ["marwari"]},
        {"label": "Agarwal/Agrawal", "group": "merchant_community", "terms": ["agarwal","agrawal"]},
        {"label": "Bania", "group": "merchant_community", "terms": ["bania"]},
        {"label": "Gupta", "group": "merchant_community", "terms": ["gupta"]},
    ]
    # Regional/cuisine
    cats += [
        {"label": "Udupi cuisine", "group": "regional", "terms": ["udupi"]},
        {"label": "Mangalorean / Tulu Nadu", "group": "regional", "terms": ["mangalorean","tulu nadu","tulu"]},
        {"label": "Konkani", "group": "regional", "terms": ["konkani"]},
        {"label": "Kodava / Coorg", "group": "regional", "terms": ["kodava","coorgi","coorg"]},
        {"label": "Places in KA", "group": "regional", "terms": ["mysore","mandya","dharwad"]},
        {"label": "Other languages", "group": "regional", "terms": ["tamil","telugu","kerala","malayali","punjabi","gujarati","gujrati"]},
    ]
    # Surname/title (ambiguous)
    cats += [
        {"label": "Gowda (often Vokkaliga)", "group": "surname_title", "terms": ["gowda"]},
        {"label": "Shetty (often Bunt)", "group": "surname_title", "terms": ["shetty"]},
        {"label": "Pai", "group": "surname_title", "terms": ["pai"]},
        {"label": "Kamath", "group": "surname_title", "terms": ["kamath"]},
        {"label": "Bhat/Bhatt", "group": "surname_title", "terms": ["bhat","bhatt"]},
        {"label": "Rao", "group": "surname_title", "terms": ["rao"]},
        {"label": "Reddy", "group": "surname_title", "terms": ["reddy"]},
        {"label": "Naidu", "group": "surname_title", "terms": ["naidu"]},
        {"label": "Naik/Nayak", "group": "surname_title", "terms": ["naik","nayak"]},
        {"label": "Acharya/Achari/Jois/Sharma/Murthy/Sastry/Kulkarni/Joshi/Dixit", "group": "surname_title", "terms": ["acharya","achari","jois","sharma","murthy","sastry","kulkarni","joshi","dixit"]},
    ]
    # Expand transliterations
    for cat in cats:
        all_terms = set()
        for t in cat["terms"]:
            all_terms.update(translit_variants(t))
        cat["terms"] = sorted(all_terms)
    return cats

CATS = taxonomy()

# Compile regexes

def compile_patterns(cats: List[Dict[str, Any]]):
    compiled = []
    for cat in cats:
        term_patterns = []
        for term in cat["terms"]:
            t = re.escape(term)
            pat = re.compile(rf"(?<![A-Za-z0-9]){t}(?![A-Za-z0-9])", flags=re.IGNORECASE)
            term_patterns.append((term, pat))
        compiled.append({"label": cat["label"], "group": cat["group"], "patterns": term_patterns})
    return compiled

COMPILED = compile_patterns(CATS)

# ------------------------------- Matching -----------------------------------

def match_restaurants(
    restaurants: List[Dict[str, Any]],
    compiled_taxonomy: List[Dict[str, Any]],
    *,
    enable_fuzzy: bool = True,
    max_edit_distance: int = 1,
) -> List[Dict[str, Any]]:
    TERM_INDEX: Dict[str, List[Tuple[str,str]]] = defaultdict(list)
    for cat in compiled_taxonomy:
        for term, _ in cat["patterns"]:
            TERM_INDEX[term].append((cat["label"], cat["group"]))

    rows: List[Dict[str, Any]] = []
    for r in restaurants:
        nm = r.get("name", ""); norm = normalize_text(nm)
        token_set = set(tokenize_simple(norm))
        hits: List[Dict[str, str]] = []
        for cat in compiled_taxonomy:
            for term, pat in cat["patterns"]:
                if pat.search(norm):
                    hits.append({"term": term, "label": cat["label"], "group": cat["group"], "how": "regex"})
        if enable_fuzzy and max_edit_distance > 0:
            for token in token_set:
                for term, lg_list in TERM_INDEX.items():
                    if " " in term:
                        continue
                    if abs(len(token) - len(term)) > max_edit_distance:
                        continue
                    # fast path exact already captured; still fine if re-added
                    # but we avoid duplicates by (term,label)
                    d = levenshtein(token, term)
                    if d <= max_edit_distance:
                        already = {(h["term"], h["label"]) for h in hits}
                        for label, group in lg_list:
                            if (term, label) not in already:
                                hits.append({"term": term, "label": label, "group": group, "how": f"fuzzy(d={d})"})
        out = dict(r)
        out["matches"] = hits
        rows.append(out)
    return rows

# ------------------------------- Summaries ----------------------------------

def summarize(rows: List[Dict[str, Any]], *, denominator_n: Optional[int] = None) -> Dict[str, Any]:
    n_base = len(rows)
    n = n_base if denominator_n is None else denominator_n

    group_to_ids: Dict[str, set] = defaultdict(set)
    label_to_ids: Dict[str, set] = defaultdict(set)
    term_to_ids: Dict[str, set] = defaultdict(set)
    how_counter: Counter = Counter()

    for row in rows:
        pid = row.get("place_id")
        labs = {(m["label"], m["group"]) for m in row.get("matches", [])}
        for label, group in labs:
            label_to_ids[label].add(pid)
            group_to_ids[group].add(pid)
        for m in row.get("matches", []):
            term_to_ids[m["term"]].add(pid)
            how_counter[m.get("how", "regex")] += 1

    group_counts = {g: len(s) for g, s in group_to_ids.items()}
    label_counts = {l: len(s) for l, s in label_to_ids.items()}
    term_counts = {t: len(s) for t, s in term_to_ids.items()}

    top_groups = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
    top_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
    top_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)

    group_prevalence = []
    for g, c in top_groups:
        lo, hi = wilson_ci(c, n)
        group_prevalence.append({"group": g, "count": c, "n": n, "p": (c/n) if n else 0.0, "ci_low": lo, "ci_high": hi})

    return {
        "rows_scored": n_base,
        "denominator_used": n,
        "group_counts": group_counts,
        "label_counts": label_counts,
        "term_counts": term_counts,
        "top_groups": top_groups,
        "top_labels": top_labels,
        "top_terms": top_terms,
        "group_prevalence": group_prevalence,
        "match_hows": dict(how_counter),
    }

# ------------------------------- I/O helpers --------------------------------

def read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def write_outputs(rows: List[Dict[str, Any]], summary: Dict[str, Any], basepath: str, scope: str) -> None:
    with open(f"{basepath}_{scope}_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(f"{basepath}_{scope}_matches.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{basepath}_{scope}_group_prevalence.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["group","count","n","p","ci_low","ci_high"])
        for rec in summary["group_prevalence"]:
            w.writerow([rec["group"], rec["count"], rec["n"], rec["p"], rec["ci_low"], rec["ci_high"]])
    with open(f"{basepath}_{scope}_label_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["label","count"]) 
        for label, c in sorted(summary["label_counts"].items(), key=lambda x: x[1], reverse=True):
            w.writerow([label, c])

# ------------------------------ Denominator math ----------------------------

def dedupe(restaurants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out: List[Dict[str, Any]] = []
    for r in restaurants:
        key = (r.get("place_id"), normalize_text(r.get("name", "")))
        if key not in seen:
            seen.add(key); out.append(r)
    return out


def denominator_report_and_value(rows: List[Dict[str, Any]], *, denominator: str) -> Tuple[int, Optional[Dict[str, float]]]:
    places = [r for r in rows if r.get("source") == "places"]
    osm = [r for r in rows if r.get("source") == "osm"]
    A_ids = {r.get("place_id") for r in dedupe(places)}
    B_ids = {r.get("place_id") for r in dedupe(osm)}
    union_n = len({r.get("place_id") for r in dedupe(places + osm)})

    print("\n" + "=" * 72)
    print("📏  DENOMINATOR REPORT")
    print("=" * 72)
    print(f"Places unique (A) : {len(A_ids)}")
    print(f"OSM unique (B)    : {len(B_ids)}")
    print(f"Union |A ∪ B|     : {union_n}")
    overlap = len(A_ids & B_ids)
    print(f"Overlap |A ∩ B|   : {overlap}")

    cr_est = None
    if denominator == "cr" and A_ids and B_ids and overlap > 0:
        cr_est = capture_recapture(len(A_ids), len(B_ids), overlap)
        print(f"CR N̂ ≈ {cr_est['N_hat']:.0f} (± {1.96*cr_est['se']:.0f}) 95% CI [{cr_est['ci_low']:.0f}, {cr_est['ci_high']:.0f}]")
        n = int(round(cr_est["N_hat"]))
    else:
        if denominator == "cr":
            print("Capture–recapture not available → using observed union")
        n = union_n

    return n, cr_est

# ------------------------------- Orchestration ------------------------------

def analyze(files: Iterable[str], *, group_by_region: bool, denominator: str, enable_fuzzy: bool, max_edit_distance: int, basepath: str, focus_upper_only_print: bool) -> None:
    # Expand globs
    expanded: List[str] = []
    for p in files:
        expanded.extend(glob.glob(p))
    if not expanded:
        raise SystemExit("No input files found")

    # Read and group
    all_rows: List[Dict[str, Any]] = []
    for p in expanded:
        all_rows.extend(read_jsonl(p))
    if not all_rows:
        raise SystemExit("Input files were empty or unreadable")

    if group_by_region:
        by_reg: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in all_rows:
            by_reg[r.get("region_id") or "unknown"].append(r)
        # Per region
        for rid, rows in sorted(by_reg.items()):
            print("\n" + "-" * 72)
            print(f"Region: {rid} — {rows[0].get('region_name','')}")
            n, _cr = denominator_report_and_value(rows, denominator=denominator)
            rows_dedup = dedupe(rows)
            matched = match_restaurants(rows_dedup, COMPILED, enable_fuzzy=enable_fuzzy, max_edit_distance=max_edit_distance)
            summary = summarize(matched, denominator_n=n)
            scope = f"region_{rid}"
            print(f"Rows scored: {len(matched)} | Denominator used: {n}")
            # Print concise group summary
            groups = summary["top_groups"]
            hdr = "— Upper-caste only —" if focus_upper_only_print else "— All groups —"
            print(hdr)
            for g, c in groups:
                if focus_upper_only_print and g != "upper_caste":
                    continue
                pct = (100.0 * c / n) if n else 0.0
                print(f"  • {g:17s}: {c:4d}  ({pct:.2f}%)")
            write_outputs(matched, summary, basepath, scope)

    # Combined scope
    print("\n" + "-" * 72)
    print("Combined (all regions)")
    n_all, _cr_all = denominator_report_and_value(all_rows, denominator=denominator)
    rows_all = dedupe(all_rows)
    matched_all = match_restaurants(rows_all, COMPILED, enable_fuzzy=enable_fuzzy, max_edit_distance=max_edit_distance)
    summary_all = summarize(matched_all, denominator_n=n_all)
    scope_all = "combined"
    write_outputs(matched_all, summary_all, basepath, scope_all)
    print(f"Rows scored: {len(matched_all)} | Denominator used: {n_all}")

# ------------------------------- CLI/Notebook -------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze caste-coded branding from raw restaurant catalogs")
    parser.add_argument("--inputs", nargs="+", help="One or more *_raw_collection.jsonl files (globs ok)")
    parser.add_argument("--group-by-region", action="store_true", help="Report per region as well as combined")
    parser.add_argument("--denominator", choices=["observed","cr"], default="observed")
    parser.add_argument("--enable-fuzzy", action="store_true")
    parser.add_argument("--max-edit-distance", type=int, default=1)
    parser.add_argument("--basepath", type=str, default=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--focus-upper-only-print", action="store_true")

    import sys, shlex
    in_ipykernel = ('ipykernel' in sys.modules) or sys.argv[0].endswith('ipykernel_launcher.py')
    if argv is None and in_ipykernel:
        argv = []
        extra = os.environ.get("ANALYZE_ARGS");
        if extra:
            argv = shlex.split(extra)
        args, _ = parser.parse_known_args(argv)
        return args
    if argv is None:
        return parser.parse_args()
    args, _ = parser.parse_known_args(argv)
    return args


def analyze_run_notebook(files: Iterable[str], *, group_by_region: bool = True, denominator: str = "observed", enable_fuzzy: bool = True, max_edit_distance: int = 1, basepath: str = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}", focus_upper_only_print: bool = False):
    analyze(files, group_by_region=group_by_region, denominator=denominator, enable_fuzzy=enable_fuzzy, max_edit_distance=max_edit_distance, basepath=basepath, focus_upper_only_print=focus_upper_only_print)


def main() -> None:
    args = parse_args()
    analyze(args.inputs, group_by_region=args.group_by_region, denominator=args.denominator, enable_fuzzy=args.enable_fuzzy, max_edit_distance=args.max_edit_distance, basepath=args.basepath, focus_upper_only_print=args.focus_upper_only_print)


if __name__ == "__main__":
    main()
