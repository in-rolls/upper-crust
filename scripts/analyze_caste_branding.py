#!/usr/bin/env python3
"""Estimate the prevalence of caste/community-coded restaurant names.

Reads raw catalogs (JSONL from the collector), matches names against a curated
taxonomy of caste/community terms, and writes per-region and combined
prevalence estimates.

Method choices, and why:
  * Matching is exact word-boundary regex over hand-curated spelling variants.
    An earlier version fuzzy-matched at edit distance 1, which made the largest
    categories 83-97% false positives ("chats" -> Bhat, "Sai" -> Pai); every
    variant here is a spelling a human would accept for the term.
  * Non-Latin names (Kannada/Tamil/Telugu/Malayalam/Devanagari) are
    transliterated to Latin (IAST via indic-transliteration, diacritics then
    stripped) before matching, so they can score instead of silently sitting
    in the denominator.
  * Places and OSM rows for the same restaurant are linked by normalized name
    plus proximity (<= 200 m). Linked pairs count once in the denominator, and
    the overlap feeds a Chapman capture-recapture estimate of the true number
    of restaurants, reported alongside the observed-union denominator.

Usage:
  python scripts/analyze_caste_branding.py \
      --inputs 'data/restaurants_2025_08_22_*_raw_collection.jsonl' \
      --basepath data/analysis_2026_08_30
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from indic_transliteration import sanscript

# ----------------------------- Normalization --------------------------------

# Unicode block -> sanscript scheme, for scripts present in the data.
_SCRIPT_RANGES = [
    (0x0900, 0x097F, sanscript.DEVANAGARI),
    (0x0B80, 0x0BFF, sanscript.TAMIL),
    (0x0C00, 0x0C7F, sanscript.TELUGU),
    (0x0C80, 0x0CFF, sanscript.KANNADA),
    (0x0D00, 0x0D7F, sanscript.MALAYALAM),
]


def detect_scripts(s: str) -> List[str]:
    found = []
    for ch in s:
        cp = ord(ch)
        for lo, hi, scheme in _SCRIPT_RANGES:
            if lo <= cp <= hi and scheme not in found:
                found.append(scheme)
    return found


def romanize(s: str) -> str:
    """Transliterate any Indic-script runs to Latin; Latin text passes through."""
    for scheme in detect_scripts(s):
        s = sanscript.transliterate(s, scheme, sanscript.IAST)
    return s


def normalize_text(s: str) -> str:
    s = romanize(s or "")
    s = unicodedata.normalize("NFKC", s)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", s).strip().lower()


def has_latin_letter(s: str) -> bool:
    return bool(re.search(r"[a-z]", s))


# -------------------------------- Taxonomy ----------------------------------

# label -> (group, {canonical term -> [spelling variants]}).
# Variants are hand-curated spellings only — no generated substitutions, no
# fuzzy matching. Possessives need no variants: the apostrophe is a word
# boundary, so "brahmin's" already matches "brahmin".
TAXONOMY: List[Dict[str, Any]] = [
    # Upper-caste / Brahmin communities
    {
        "label": "Brahmin (general)",
        "group": "upper_caste",
        "terms": {"brahmin": ["brahmin", "brahmins", "bramhin", "brahmana"]},
    },
    {
        "label": "Iyengar (Tamil Brahmin)",
        "group": "upper_caste",
        "terms": {
            "iyengar": ["iyengar", "iyengars", "ayyangar", "ayengar"],
            "mandyam": ["mandyam"],
        },
    },
    {
        "label": "Iyer (Tamil Brahmin)",
        "group": "upper_caste",
        "terms": {"iyer": ["iyer", "iyers", "aiyar", "aiyer", "ayyar"]},
    },
    {
        "label": "Madhva / Dvaita (Brahmin)",
        "group": "upper_caste",
        "terms": {"madhva": ["madhva", "madhwa"]},
    },
    {
        "label": "Smartha (Brahmin)",
        "group": "upper_caste",
        "terms": {"smartha": ["smartha", "smarta"]},
    },
    {
        "label": "Deshastha (Brahmin)",
        "group": "upper_caste",
        "terms": {"deshastha": ["deshastha"]},
    },
    {
        "label": "Gaud Saraswat / GSB",
        "group": "upper_caste",
        "terms": {
            "saraswat": ["saraswat", "saraswath", "gaud saraswat"],
            "gsb": ["gsb"],
        },
    },
    {
        "label": "Havyaka (Brahmin)",
        "group": "upper_caste",
        "terms": {"havyaka": ["havyaka", "havyak"]},
    },
    {
        "label": "Shivalli (Brahmin)",
        "group": "upper_caste",
        "terms": {"shivalli": ["shivalli"]},
    },
    {
        "label": "Hebbar (Brahmin - ambiguous)",
        "group": "upper_caste",
        "terms": {"hebbar": ["hebbar", "hebbars"]},
    },
    # Merchant communities
    {
        "label": "Jain",
        "group": "merchant_community",
        "terms": {"jain": ["jain", "jains"]},
    },
    {
        "label": "Marwari",
        "group": "merchant_community",
        "terms": {"marwari": ["marwari", "marwadi"]},
    },
    {
        "label": "Agarwal/Agrawal",
        "group": "merchant_community",
        "terms": {"agarwal": ["agarwal", "agrawal", "aggarwal"]},
    },
    {"label": "Bania", "group": "merchant_community", "terms": {"bania": ["bania"]}},
    {
        "label": "Gupta",
        "group": "merchant_community",
        "terms": {"gupta": ["gupta", "guptas"]},
    },
    # v2 (frozen 2026-08-31, before the sampled collections): Tamil and
    # North Indian communities the FN screen and the FN examples surfaced.
    {
        "label": "Chettiar (Tamil merchant)",
        "group": "merchant_community",
        "terms": {"chettiar": ["chettiar", "chettiyar", "chetty", "chetti"]},
    },
    # Regional / cuisine identities
    {
        "label": "Udupi cuisine",
        "group": "regional",
        "terms": {"udupi": ["udupi", "udipi", "udupi's", "udupis"]},
    },
    {
        "label": "Mangalorean / Tulu Nadu",
        "group": "regional",
        "terms": {"mangalorean": ["mangalorean"], "tulu": ["tulu", "tulu nadu"]},
    },
    {"label": "Konkani", "group": "regional", "terms": {"konkani": ["konkani"]}},
    {
        "label": "Kodava / Coorg",
        "group": "regional",
        "terms": {"kodava": ["kodava"], "coorg": ["coorg", "coorgi", "kodagu"]},
    },
    {
        "label": "Places in KA",
        "group": "regional",
        "terms": {
            "mysore": ["mysore", "mysuru"],
            "mandya": ["mandya"],
            "dharwad": ["dharwad", "dharwar"],
        },
    },
    {
        "label": "Other languages",
        "group": "regional",
        "terms": {
            "tamil": ["tamil"],
            "telugu": ["telugu"],
            "kerala": ["kerala"],
            "malayali": ["malayali", "malayalee"],
            "punjabi": ["punjabi"],
            "gujarati": ["gujarati", "gujrati"],
            "andhra": ["andhra"],
        },
    },
    {
        "label": "Chettinad cuisine",
        "group": "regional",
        "terms": {"chettinad": ["chettinad", "chettinadu"]},
    },
    # Surnames / titles (caste-associated but individually ambiguous)
    {
        "label": "Gowda (often Vokkaliga)",
        "group": "surname_title",
        "terms": {"gowda": ["gowda", "gowdas", "gowdru"]},
    },
    {
        "label": "Shetty (often Bunt)",
        "group": "surname_title",
        "terms": {"shetty": ["shetty", "shetti", "shettys", "shetty's"]},
    },
    {"label": "Pai", "group": "surname_title", "terms": {"pai": ["pai"]}},
    {
        "label": "Kamath",
        "group": "surname_title",
        "terms": {"kamath": ["kamath", "kamat"]},
    },
    {
        "label": "Bhat/Bhatt",
        "group": "surname_title",
        "terms": {"bhat": ["bhat", "bhatt", "bhats"]},
    },
    {"label": "Rao", "group": "surname_title", "terms": {"rao": ["rao"]}},
    {
        "label": "Reddy",
        "group": "surname_title",
        "terms": {"reddy": ["reddy", "reddys"]},
    },
    {"label": "Naidu", "group": "surname_title", "terms": {"naidu": ["naidu"]}},
    {
        "label": "Tamil caste surnames (Pillai/Mudaliar/Nadar/Gounder/Thevar/Naicker/Pandian)",
        "group": "surname_title",
        "terms": {
            "pillai": ["pillai"],
            "mudaliar": ["mudaliar", "mudaliyar"],
            "nadar": ["nadar"],
            "gounder": ["gounder"],
            "thevar": ["thevar"],
            "naicker": ["naicker"],
            "pandian": ["pandian", "pandiyan"],
        },
    },
    {
        "label": "North/West caste surnames (Yadav/Thakur/Khatri/Patel/Patil)",
        "group": "surname_title",
        "terms": {
            "yadav": ["yadav", "yadava"],
            "thakur": ["thakur"],
            "khatri": ["khatri"],
            "patel": ["patel"],
            "patil": ["patil"],
        },
    },
    {
        "label": "Naik/Nayak",
        "group": "surname_title",
        "terms": {"naik": ["naik", "nayak"]},
    },
    {
        "label": "Acharya/Jois/Sharma/Murthy/Sastry/Kulkarni/Joshi/Dixit",
        "group": "surname_title",
        "terms": {
            "acharya": ["acharya", "achari"],
            "jois": ["jois"],
            "sharma": ["sharma"],
            "murthy": ["murthy", "murty", "moorthy"],
            "sastry": ["sastry", "sastri", "shastry", "shastri"],
            "kulkarni": ["kulkarni"],
            "joshi": ["joshi"],
            "dixit": ["dixit", "dikshit"],
        },
    },
]


def compile_taxonomy() -> List[Dict[str, Any]]:
    compiled = []
    for cat in TAXONOMY:
        pats = []
        for canonical, variants in cat["terms"].items():
            for v in variants:
                pat = re.compile(rf"(?<![a-z0-9]){re.escape(v)}(?![a-z0-9])")
                pats.append((canonical, v, pat))
        compiled.append(
            {"label": cat["label"], "group": cat["group"], "patterns": pats}
        )
    return compiled


# ------------------------------- Matching -----------------------------------


def match_restaurants(
    rows: List[Dict[str, Any]], compiled: List[Dict[str, Any]]
) -> None:
    """Attach a ``matches`` list to each row in place.

    A restaurant counts once per (label, canonical term) no matter how many
    variants hit — the old analyzer counted "udupi" and "udupis" as two terms.
    """
    for r in rows:
        norm = normalize_text(r.get("name", ""))
        r["name_normalized"] = norm
        hits = []
        seen = set()
        for cat in compiled:
            for canonical, variant, pat in cat["patterns"]:
                if (cat["label"], canonical) in seen:
                    continue
                if pat.search(norm):
                    seen.add((cat["label"], canonical))
                    hits.append(
                        {
                            "term": canonical,
                            "variant": variant,
                            "label": cat["label"],
                            "group": cat["group"],
                        }
                    )
        r["matches"] = hits


# ------------------------- Dedup and source linkage --------------------------


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def dedupe_within_source(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in rows:
        key = (r.get("place_id"), normalize_text(r.get("name", "")))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _name_tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", normalize_text(s)))


def link_sources(
    rows: List[Dict[str, Any]], *, max_dist_m: float = 200.0, min_jaccard: float = 0.5
) -> Tuple[List[Dict[str, Any]], int, int, int]:
    """Collapse Places/OSM rows describing the same restaurant.

    Link rule: token Jaccard >= min_jaccard AND coordinates within max_dist_m.
    Same-name pairs farther apart are chain branches, not the same place (in
    the blr data the distance distribution of same-name cross-source pairs is
    bimodal: <=200 m or >6 km). Rows are copied so callers can reuse the same
    input dicts across scopes. Linked pairs keep the Places row and record the
    OSM id on it. Returns (entities, n_places, n_osm, n_linked).
    """
    places = [
        dict(r)
        for r in dedupe_within_source([r for r in rows if r.get("source") == "places"])
    ]
    osm = [
        dict(r)
        for r in dedupe_within_source([r for r in rows if r.get("source") == "osm"])
    ]

    # ~500 m grid buckets so candidate search is local, not O(places x osm)
    grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)

    def cell(lat: float, lon: float) -> Tuple[int, int]:
        return (round(lat * 200), round(lon * 200))

    for p in places:
        if isinstance(p.get("lat"), (int, float)) and isinstance(
            p.get("lon"), (int, float)
        ):
            grid[cell(p["lat"], p["lon"])].append(p)

    linked = 0
    unmatched_osm = []
    for r in osm:
        best = None
        toks = _name_tokens(r.get("name", ""))
        if toks and isinstance(r.get("lat"), (int, float)):
            c0 = cell(r["lat"], r["lon"])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for cand in grid[(c0[0] + dx, c0[1] + dy)]:
                        if "linked_osm_id" in cand:
                            continue
                        if (
                            haversine_m(r["lat"], r["lon"], cand["lat"], cand["lon"])
                            > max_dist_m
                        ):
                            continue
                        ctoks = _name_tokens(cand.get("name", ""))
                        if not ctoks:
                            continue
                        j = len(toks & ctoks) / len(toks | ctoks)
                        if j >= min_jaccard and (best is None or j > best[0]):
                            best = (j, cand)
        if best is not None:
            best[1]["linked_osm_id"] = r.get("place_id")
            linked += 1
        else:
            unmatched_osm.append(r)

    return places + unmatched_osm, len(places), len(osm), linked


# ------------------------------- Statistics ---------------------------------


def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def chapman_estimate(n_a: int, n_b: int, m: int) -> Optional[Dict[str, Any]]:
    if n_a <= 0 or n_b <= 0 or m <= 0:
        return None
    n_hat = (n_a + 1) * (n_b + 1) / (m + 1) - 1
    var = ((n_a + 1) * (n_b + 1) * (n_a - m) * (n_b - m)) / ((m + 1) ** 2 * (m + 2))
    se = math.sqrt(max(var, 0.0))
    return {
        "N_hat": n_hat,
        "se": se,
        "ci_low": max(0.0, n_hat - 1.96 * se),
        "ci_high": n_hat + 1.96 * se,
    }


# ------------------------------- Summaries ----------------------------------


def summarize(
    entities: List[Dict[str, Any]],
    *,
    n_places: int,
    n_osm: int,
    n_linked: int,
    invocation: Dict[str, Any],
) -> Dict[str, Any]:
    n = len(entities)
    group_ids: Dict[str, set] = defaultdict(set)
    label_ids: Dict[str, set] = defaultdict(set)
    term_ids: Dict[str, set] = defaultdict(set)
    unscorable = 0
    for r in entities:
        if not has_latin_letter(r.get("name_normalized", "")):
            unscorable += 1
        pid = r.get("place_id")
        for m in r["matches"]:
            group_ids[m["group"]].add(pid)
            label_ids[m["label"]].add(pid)
            term_ids[m["term"]].add(pid)

    # Chapman assumes independent samples with homogeneous capture and perfect
    # matching. Places is a prominence-ranked truncated grid, OSM is volunteer
    # coverage, and linkage misses spelling divergence, so m is a floor and
    # N_hat a wild overestimate. Kept in the JSON for the record, flagged as
    # not credible; observed union is the denominator everywhere.
    cr = chapman_estimate(n_places, n_osm, n_linked)
    if cr:
        cr["credible"] = False
        cr["why_not_credible"] = (
            "linkage undercounts overlap and capture "
            "probabilities are heterogeneous across sources"
        )
    group_prevalence = []
    for g in sorted(group_ids, key=lambda g: -len(group_ids[g])):
        c = len(group_ids[g])
        lo, hi = wilson_ci(c, n)
        group_prevalence.append(
            {
                "group": g,
                "count": c,
                "n": n,
                "p": c / n if n else 0.0,
                "ci_low": lo,
                "ci_high": hi,
            }
        )

    return {
        "invocation": invocation,
        "n_entities": n,
        "n_places": n_places,
        "n_osm": n_osm,
        "n_linked_across_sources": n_linked,
        "n_unscorable_after_transliteration": unscorable,
        "capture_recapture": cr,
        "group_counts": {g: len(s) for g, s in group_ids.items()},
        "label_counts": {lab: len(s) for lab, s in label_ids.items()},
        "term_counts": {t: len(s) for t, s in term_ids.items()},
        "group_prevalence": group_prevalence,
    }


# ------------------------------- I/O helpers --------------------------------


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_outputs(
    entities: List[Dict[str, Any]],
    summary: Dict[str, Any],
    basepath: str,
    scope: str,
    *,
    write_matches: bool = True,
) -> None:
    with open(f"{basepath}_{scope}_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    if write_matches:
        with open(f"{basepath}_{scope}_matches.jsonl", "w", encoding="utf-8") as f:
            for r in entities:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(
        f"{basepath}_{scope}_group_prevalence.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["group", "count", "n", "p", "ci_low", "ci_high"])
        for rec in summary["group_prevalence"]:
            w.writerow(
                [
                    rec["group"],
                    rec["count"],
                    rec["n"],
                    f"{rec['p']:.6f}",
                    f"{rec['ci_low']:.6f}",
                    f"{rec['ci_high']:.6f}",
                ]
            )
    with open(
        f"{basepath}_{scope}_label_counts.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["label", "count"])
        for label, c in sorted(summary["label_counts"].items(), key=lambda x: -x[1]):
            w.writerow([label, c])


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


# ------------------------------- Orchestration ------------------------------


def analyze(files: Iterable[str], *, basepath: str, link_dist_m: float) -> None:
    expanded: List[str] = []
    for p in files:
        expanded.extend(sorted(glob.glob(p)))
    if not expanded:
        raise SystemExit("No input files found")

    all_rows: List[Dict[str, Any]] = []
    for p in expanded:
        all_rows.extend(read_jsonl(p))

    invocation = {
        "argv": sys.argv,
        "inputs": expanded,
        "git_commit": git_commit_hash(),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    compiled = compile_taxonomy()

    by_region: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in all_rows:
        by_region[r.get("region_id") or "unknown"].append(r)

    scopes = [(f"region_{rid}", rows) for rid, rows in sorted(by_region.items())]
    scopes.append(("combined", all_rows))

    for scope, rows in scopes:
        entities, n_places, n_osm, n_linked = link_sources(rows, max_dist_m=link_dist_m)
        match_restaurants(entities, compiled)
        summary = summarize(
            entities,
            n_places=n_places,
            n_osm=n_osm,
            n_linked=n_linked,
            invocation=invocation,
        )
        write_outputs(
            entities, summary, basepath, scope, write_matches=(scope != "combined")
        )
        print(
            f"{scope}: n={summary['n_entities']} "
            f"(places {n_places}, osm {n_osm}, linked {n_linked}; "
            f"unscorable {summary['n_unscorable_after_transliteration']})"
        )
        for rec in summary["group_prevalence"]:
            print(
                f"  {rec['group']:20s} {rec['count']:4d}  {100*rec['p']:.2f}% "
                f"[{100*rec['ci_low']:.2f}, {100*rec['ci_high']:.2f}]"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate prevalence of caste/community-coded restaurant names"
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="*_raw_collection.jsonl files (globs ok)",
    )
    parser.add_argument(
        "--basepath", default=f"data/analysis_{datetime.now():%Y_%m_%d}"
    )
    parser.add_argument(
        "--link-dist-m",
        type=float,
        default=200.0,
        help="max meters between Places and OSM points to link",
    )
    args = parser.parse_args()
    analyze(args.inputs, basepath=args.basepath, link_dist_m=args.link_dist_m)


if __name__ == "__main__":
    main()
