#!/usr/bin/env python3
"""Extract hotel/restaurant trade sections from digitized colonial directories.

Source: the Asylum Press Almanack & Directory of Madras and Southern India,
five editions (1918, 1919, 1924, 1925, 1928) digitized by the Digital Library
of India on archive.org, full OCR text. Each town's commercial section lists
trades under short headings ("Hotels.", "Hotels and Restaurants.") with
establishment names and often proprietors.

The OCR is too noisy for fully automatic parsing, so this script does the
mechanical half: find every hotel/restaurant heading, dump the section with
surrounding context to one review file per edition. The tidy CSV
(data/historical/eating_houses_1918_1928.csv) is then hand-built from those
review files, which keeps every judgment visible and checkable against the
raw OCR.

Usage:
  python scripts/historical_directories.py            # extract sections
  python scripts/historical_directories.py --download # fetch texts first
"""

from __future__ import annotations

import argparse
import re
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "historical"

EDITIONS = {
    1918: "in.ernet.dli.2015.83800",
    1919: "in.ernet.dli.2015.83807",
    1924: "in.ernet.dli.2015.83815",
    1925: "in.ernet.dli.2015.83823",
    1928: "in.ernet.dli.2015.109682",
}

# OCR-tolerant: B/H confusion (Botels), u/n confusion (Restanrants), stray
# spaces, and a trailing OCR particle after the period.
_H = r"[hb]ote[il][sb]?"
_R = r"resta[un]ra[nu]t[sb]?"
HEADING = re.compile(
    rf"^\s*({_H}|{_R}|{_H}\s*(and|&|«fe)\s*{_R}|"
    rf"coffee\s*{_H}|refreshment\s*rooms?)\s*[.,;:*'’]*\s*$",
    re.IGNORECASE,
)
# A short capitalized line ending in a period reads as the next trade heading.
NEXT_HEADING = re.compile(r"^\s*[A-Z][A-Za-z .,&'-]{2,35}[.,]\s*$")

CONTEXT_BEFORE = 10
MAX_SECTION = 45


def download() -> None:
    import json

    DATA.mkdir(parents=True, exist_ok=True)
    for year, ident in EDITIONS.items():
        out = DATA / f"{ident}.txt"
        if out.exists() and out.stat().st_size > 1_000_000:
            continue
        with urllib.request.urlopen(f"https://archive.org/metadata/{ident}") as r:
            files = json.load(r)["files"]
        name = next(f["name"] for f in files if f["name"].endswith("_djvu.txt"))
        url = f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}"
        print(f"{year}: downloading {name}")
        urllib.request.urlretrieve(url, out)


def extract() -> None:
    for year, ident in EDITIONS.items():
        path = DATA / f"{ident}.txt"
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        out_path = DATA / f"sections_{year}.txt"
        n_sections = 0
        with open(out_path, "w", encoding="utf-8") as out:
            for i, line in enumerate(lines):
                if not HEADING.match(line):
                    continue
                n_sections += 1
                start = max(0, i - CONTEXT_BEFORE)
                end = i + 1
                # Section runs to the next trade-like heading, capped.
                while end < min(i + MAX_SECTION, len(lines)):
                    if (
                        end > i + 2
                        and NEXT_HEADING.match(lines[end])
                        and not HEADING.match(lines[end])
                    ):
                        break
                    end += 1
                out.write(f"===== {year} line {i + 1} =====\n")
                for j in range(start, i):
                    out.write(f"  ctx | {lines[j]}\n")
                for j in range(i, end):
                    out.write(f"      | {lines[j]}\n")
                out.write("\n")
        print(f"{year}: {n_sections} sections -> {out_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract historical hotel sections")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
    extract()


if __name__ == "__main__":
    main()
