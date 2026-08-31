#!/usr/bin/env python3
"""Adjudicate dictionary matches with a local open-weights LLM (Qwen3-8B).

Two tasks:
  A. Every (restaurant, label) pair the dictionary flagged: does the matched
     word really refer to that caste/community in this name, or is it an
     unrelated word (a person's given name, a dish, a place)? This measures
     the dictionary's false-positive rate exactly, not by sampling.
  B. A seeded random sample of unmatched names per region: does the name
     carry caste/community branding the dictionary missed? This estimates the
     false-negative rate.

Qwen3-8B via Ollama (temperature 0, pinned model) so anyone can re-run the
adjudication for free. Results append to a JSONL checkpoint after every batch;
re-running skips finished items, so a crash loses at most one batch.

Usage:
  python scripts/adjudicate_matches.py --basepath data/analysis_2026_08_30 \
      --out data/adjudication_2026_08_30.jsonl
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import re
import sys
import urllib.request
from typing import Any, Dict, List

MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"
BATCH = 20
FN_SAMPLE_PER_REGION = 500
SEED = 42

PROMPT_A_CASTE = """\
These are restaurant names from {city}, India. In each, a specific word was \
flagged as possibly referring to an Indian caste or community. Judge ONLY \
whether the flagged word, in this name, is used as that caste/community label \
or as a caste-linked surname/title of a person or family. A surname counts \
even inside a person's full name. Answer false only when the word is really a \
different word (a dish, a deity or given name, a place, a foreign word) that \
merely resembles the term.
Examples: "N Santhosh Shetty" / Shetty -> true (surname). "Sangeetha \
Moorthy" / Murthy -> true (surname). "Samosa And Chats shop" / Bhat -> false \
(chats is a dish). "Sri Sai Sagar" / Pai -> false (Sai is a deity name).
Reply with JSON only: {{"answers": [{{"id": <id>, "genuine": true|false, \
"reason": "<max 10 words>"}}]}}

{items}"""

PROMPT_A_REGIONAL = """\
These are restaurant names from {city}, India. In each, a specific word was \
flagged as possibly signaling a regional, linguistic, or cuisine identity \
(e.g. Udupi, Kerala, Punjabi, Mysore-style). Judge ONLY whether the flagged \
word is part of the restaurant's branding — signaling origin, cuisine, or \
community identity — as opposed to incidental text such as the restaurant's \
own address, locality, or branch tag.
Examples: "Kerala Corner" / Kerala -> true (cuisine identity). "Hotel New \
Punjabi Dhaba" / Punjabi -> true. "Domino's Pizza | Vivekananda Nagar, \
Mysuru" / Mysore -> false (address text). "JP nagar near ring road Mysore" / \
Mysore -> false (address).
Reply with JSON only: {{"answers": [{{"id": <id>, "genuine": true|false, \
"reason": "<max 10 words>"}}]}}

{items}"""

PROMPT_B = """\
These are restaurant names from {city}, India. For each, judge whether the \
name contains an EXPLICIT Indian caste, sub-caste, or community reference: a \
caste or community label (Brahmin, Iyer, Jain, Marwari), a caste-linked \
surname (Shetty, Reddy, Gowda, Bhat), or a regional/cuisine identity used as \
branding (Udupi, Andhra, Kerala). Deity and given names (Krishna, Sai, \
Ganesh), dish names, dynasties, and address text do NOT count. Reply with \
JSON only: {{"answers": [{{"id": <id>, "caste_coded": true|false, "term": \
"<the referencing word, or empty>", "reason": "<max 10 words>"}}]}}

{items}"""

CITY = {"blr": "Bengaluru", "maa": "Chennai", "mys": "Mysuru"}


def ollama_chat(prompt: str) -> Dict[str, Any]:
    body = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        content = json.load(resp)["message"]["content"]
    return json.loads(content)


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_done(out_path: str) -> set:
    done = set()
    try:
        for r in read_jsonl(out_path):
            done.add(r["item_id"])
    except FileNotFoundError:
        pass
    return done


def run_batches(
    items: List[Dict[str, Any]], template: str, region: str, out_path: str, done: set
) -> None:
    todo = [it for it in items if it["item_id"] not in done]
    for i in range(0, len(todo), BATCH):
        chunk = todo[i : i + BATCH]
        lines = []
        for j, it in enumerate(chunk, start=1):
            if it["task"] in ("verify_match", "verify_screen"):
                lines.append(
                    f'{j}. name: "{it["name"]}", flagged word: '
                    f'"{it["variant"]}", term: {it["term"]} ({it["label"]})'
                )
            else:
                lines.append(f'{j}. name: "{it["name"]}"')
        prompt = template.format(city=CITY.get(region, region), items="\n".join(lines))
        try:
            parsed = ollama_chat(prompt)
            answers = {}
            for a in parsed.get("answers", []):
                try:
                    answers[int(a.get("id"))] = a
                except (TypeError, ValueError):
                    continue
        except Exception as e:  # keep going; unanswered items retry on re-run
            print(f"  batch failed ({e}); will retry on next run", file=sys.stderr)
            continue
        with open(out_path, "a", encoding="utf-8") as f:
            for j, it in enumerate(chunk, start=1):
                a = answers.get(j)
                if a is None:
                    continue
                rec = dict(it)
                rec["verdict"] = a
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n_done = min(i + BATCH, len(todo))
        print(f"  {region} {chunk[0]['task']}: {n_done}/{len(todo)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM adjudication of dictionary matches"
    )
    parser.add_argument(
        "--basepath", required=True, help="basepath used for the analyzer run"
    )
    parser.add_argument("--out", required=True, help="checkpoint JSONL to append to")
    parser.add_argument("--fn-sample", type=int, default=FN_SAMPLE_PER_REGION)
    parser.add_argument(
        "--pilot",
        type=int,
        default=0,
        help="only process this many items per task (0 = all)",
    )
    args = parser.parse_args()

    done = load_done(args.out)
    rng = random.Random(SEED)

    for path in sorted(glob.glob(f"{args.basepath}_region_*_matches.jsonl")):
        m = re.search(r"region_(\w+)_matches", path)
        region = m.group(1) if m else "unknown"
        rows = read_jsonl(path)

        # One verdict per distinct (normalized name, label): chains like
        # "Sree Gupta Bhavan" get judged once, and the estimator script joins
        # the verdict back to every branch.
        task_a_caste, task_a_regional, unmatched = [], [], []
        seen_a = set()
        for r in rows:
            if r["matches"]:
                for mt in r["matches"]:
                    key = f"A:{r['name_normalized']}:{mt['label']}"
                    if key in seen_a:
                        continue
                    seen_a.add(key)
                    item = {
                        "task": "verify_match",
                        "region": region,
                        "item_id": key,
                        "name": r["name"],
                        "name_normalized": r["name_normalized"],
                        "term": mt["term"],
                        "variant": mt["variant"],
                        "label": mt["label"],
                        "group": mt["group"],
                    }
                    (
                        task_a_regional if mt["group"] == "regional" else task_a_caste
                    ).append(item)
            else:
                unmatched.append(r)

        sample = rng.sample(unmatched, min(args.fn_sample, len(unmatched)))
        task_b, seen_b = [], set()
        for r in sample:
            key = f"B:{r['name_normalized']}"
            if key in seen_b:
                continue
            seen_b.add(key)
            task_b.append(
                {
                    "task": "screen_unmatched",
                    "region": region,
                    "item_id": key,
                    "name": r["name"],
                    "name_normalized": r["name_normalized"],
                }
            )

        if args.pilot:
            task_a_caste = task_a_caste[: args.pilot]
            task_a_regional = task_a_regional[: args.pilot]
            task_b = task_b[: args.pilot]

        print(
            f"{region}: {len(task_a_caste)} caste pairs, "
            f"{len(task_a_regional)} regional pairs, "
            f"{len(task_b)} unmatched sampled"
        )
        run_batches(task_a_caste, PROMPT_A_CASTE, region, args.out, done)
        run_batches(task_a_regional, PROMPT_A_REGIONAL, region, args.out, done)
        run_batches(task_b, PROMPT_B, region, args.out, done)

        # Second pass: a screen hit only counts as a missed name if a
        # targeted verify question confirms it (the screen alone is noisy).
        verify = []
        for r in read_jsonl(args.out):
            if (
                r["task"] == "screen_unmatched"
                and r["region"] == region
                and r["verdict"].get("caste_coded") is True
            ):
                term = str(r["verdict"].get("term") or "").strip() or "unknown"
                verify.append(
                    {
                        "task": "verify_screen",
                        "region": region,
                        "item_id": f"C:{r['name_normalized']}",
                        "name": r["name"],
                        "name_normalized": r["name_normalized"],
                        "term": term,
                        "variant": term,
                        "label": "caste/community reference",
                        "group": "screen_hit",
                    }
                )
        run_batches(verify, PROMPT_A_CASTE, region, args.out, done)


if __name__ == "__main__":
    main()
