#!/usr/bin/env python3
"""Build a reproducible random sample of street-segment query points.

Design (following the geo-sampling package, whose BBBike source is currently
broken): the frame is every OSM road of the given types inside the city's
GADM 4.1 admin boundary, split into ~500 m segments; the sample is a
seeded uniform draw of segments; the query point is the segment midpoint.

Reproducibility: the raw Overpass response is archived beside the outputs
(OSM changes over time; the archive freezes the frame), the meta JSON
records the query, retrieval time, frame size, and seed, and re-running with
the archive present rebuilds the same frame without a network call.

For inclusion weights downstream, each sampled segment records how many
frame segments lie within the Places query radius of its midpoint: a
restaurant's inclusion probability is proportional to the number of sampled
circles covering it, which this count estimates locally.

Usage:
  python scripts/sample_frame.py --city Chennai --gadm-country IND \
      --n 75 --seed 42 --out-dir data/sampling
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROAD_TYPES = [
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
]
SEGMENT_M = 500.0
GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_{code}_shp.zip"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def gadm_polygon(code: str, level: int, region: str, cache_dir: Path):
    """Largest exterior ring of the named region from GADM 4.1 (pyshp)."""
    import shapefile

    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / f"gadm41_{code}_shp.zip"
    if not zip_path.exists():
        print(f"downloading GADM 4.1 {code}...")
        urllib.request.urlretrieve(GADM_URL.format(code=code), zip_path)
    with zipfile.ZipFile(zip_path) as z:
        base = f"gadm41_{code}_{level}"
        for ext in (".shp", ".dbf", ".shx"):
            z.extract(base + ext, cache_dir)
    sf = shapefile.Reader(str(cache_dir / base))
    name_idx = [i for i, f in enumerate(sf.fields[1:]) if f[0] == f"NAME_{level}"][0]
    for rec, shape in zip(sf.records(), sf.shapes()):
        if rec[name_idx] == region:
            parts = list(shape.parts) + [len(shape.points)]
            rings = [
                shape.points[parts[i] : parts[i + 1]] for i in range(len(parts) - 1)
            ]
            ring = max(rings, key=len)
            return [(lat, lon) for lon, lat in ring]
    raise SystemExit(f"region {region!r} not found in GADM {code} level {level}")


def point_in_polygon(lat, lon, polygon):
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        la1, lo1 = polygon[i]
        la2, lo2 = polygon[j]
        if (lo1 > lon) != (lo2 > lon) and lat < (la2 - la1) * (lon - lo1) / (
            lo2 - lo1
        ) + la1:
            inside = not inside
        j = i
    return inside


def fetch_roads(polygon, archive_path: Path):
    """Query by bounding box (Overpass rejects huge poly strings); the
    caller clips segments to the polygon afterward."""
    if archive_path.exists():
        print(f"using archived Overpass response {archive_path.name}")
        with gzip.open(archive_path, "rt", encoding="utf-8") as f:
            return json.load(f), None
    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    types = "|".join(ROAD_TYPES)
    mirrors = [
        OVERPASS_URL,
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    def query_bbox(s_, w_, n_, e_):
        q = (
            f"[out:json][timeout:600];\n"
            f'way["highway"~"^({types})$"]({s_:.5f},{w_:.5f},{n_:.5f},{e_:.5f});\n'
            f"out geom;"
        )
        body = urllib.parse.urlencode({"data": q}).encode()
        for url in mirrors:
            try:
                req = urllib.request.Request(
                    url, data=body, headers={"User-Agent": "upper-crust-sampling/1.0"}
                )
                with urllib.request.urlopen(req, timeout=660) as resp:
                    return json.load(resp)
            except Exception as e:
                print(f"  {url} failed for sub-bbox: {e}")
                time.sleep(20)
        return None

    s_, w_, n_, e_ = min(lats), min(lons), max(lats), max(lons)
    print(f"querying Overpass bbox {s_:.3f},{w_:.3f},{n_:.3f},{e_:.3f}...")
    data = query_bbox(s_, w_, n_, e_)
    if data is None:
        # Big districts overload the public servers; four quadrant queries
        # merged by way id are equivalent and much lighter each.
        print("  full bbox failed; splitting into quadrants")
        mid_lat, mid_lon = (s_ + n_) / 2, (w_ + e_) / 2
        elements, seen_ways = [], set()
        for qs, qw, qn, qe in [
            (s_, w_, mid_lat, mid_lon),
            (s_, mid_lon, mid_lat, e_),
            (mid_lat, w_, n_, mid_lon),
            (mid_lat, mid_lon, n_, e_),
        ]:
            sub = query_bbox(qs, qw, qn, qe)
            if sub is None:
                raise SystemExit("all Overpass attempts failed, even quadrants")
            for el in sub.get("elements", []):
                if el["id"] not in seen_ways:
                    seen_ways.add(el["id"])
                    elements.append(el)
            time.sleep(15)
        data = {"elements": elements}
    query = f"bbox+quadrant fallback, types ^({types})$, timeout 600"
    with gzip.open(archive_path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    return data, query


def build_segments(osm):
    """Split each way's polyline into ~SEGMENT_M chunks."""
    segments = []
    for way in osm.get("elements", []):
        geom = way.get("geometry") or []
        if len(geom) < 2:
            continue
        pts = [(g["lat"], g["lon"]) for g in geom]
        start, dist = pts[0], 0.0
        prev = pts[0]
        for pt in pts[1:]:
            dist += haversine_m(prev[0], prev[1], pt[0], pt[1])
            prev = pt
            if dist >= SEGMENT_M:
                segments.append(
                    {
                        "osm_id": way["id"],
                        "osm_name": (way.get("tags") or {}).get("name", ""),
                        "osm_type": (way.get("tags") or {}).get("highway", ""),
                        "start_lat": start[0],
                        "start_long": start[1],
                        "end_lat": pt[0],
                        "end_long": pt[1],
                    }
                )
                start, dist = pt, 0.0
        if dist > 0:
            segments.append(
                {
                    "osm_id": way["id"],
                    "osm_name": (way.get("tags") or {}).get("name", ""),
                    "osm_type": (way.get("tags") or {}).get("highway", ""),
                    "start_lat": start[0],
                    "start_long": start[1],
                    "end_lat": prev[0],
                    "end_long": prev[1],
                }
            )
    for i, s in enumerate(segments):
        s["segment_id"] = i
    return segments


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible street-segment sample")
    parser.add_argument("--city", required=True, help="GADM region name, e.g. Chennai")
    parser.add_argument("--gadm-country", default="IND")
    parser.add_argument("--gadm-level", type=int, default=2)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--radius-m",
        type=float,
        default=500.0,
        help="Places query radius, for the local-density count",
    )
    parser.add_argument("--out-dir", default="data/sampling")
    parser.add_argument("--cache-dir", default="data/sampling/cache")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = args.city.lower()

    polygon = gadm_polygon(
        args.gadm_country, args.gadm_level, args.city, Path(args.cache_dir)
    )
    archive = out_dir / f"{slug}_overpass_roads.json.gz"
    osm, query = fetch_roads(polygon, archive)
    segments = build_segments(osm)
    segments = [
        s
        for s in segments
        if point_in_polygon(
            (s["start_lat"] + s["end_lat"]) / 2,
            (s["start_long"] + s["end_long"]) / 2,
            polygon,
        )
    ]
    for i, s in enumerate(segments):
        s["segment_id"] = i
    print(f"frame: {len(segments)} segments of ~{SEGMENT_M:.0f} m inside boundary")

    # Permutation design: shuffle once, take the first n. Any larger n with
    # the same seed nests the smaller sample, so tranches extend cleanly.
    rng = random.Random(args.seed)
    order = list(range(len(segments)))
    rng.shuffle(order)
    sample = [segments[i] for i in order[: min(args.n, len(segments))]]

    # Local frame density at each sampled midpoint, for inclusion weights.
    mids = [
        ((s["start_lat"] + s["end_lat"]) / 2, (s["start_long"] + s["end_long"]) / 2)
        for s in segments
    ]
    for s in sample:
        mlat = (s["start_lat"] + s["end_lat"]) / 2
        mlon = (s["start_long"] + s["end_long"]) / 2
        s["mid_lat"], s["mid_long"] = mlat, mlon
        s["frame_segments_within_radius"] = sum(
            1
            for lat, lon in mids
            if abs(lat - mlat) < 0.01
            and abs(lon - mlon) < 0.01
            and haversine_m(mlat, mlon, lat, lon) <= args.radius_m
        )

    import csv

    sample_path = out_dir / f"{slug}_segments_n{args.n}_seed{args.seed}.csv"
    cols = [
        "segment_id",
        "osm_id",
        "osm_name",
        "osm_type",
        "start_lat",
        "start_long",
        "end_lat",
        "end_long",
        "mid_lat",
        "mid_long",
        "frame_segments_within_radius",
    ]
    with open(sample_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=cols, extrasaction="ignore", lineterminator="\n"
        )
        w.writeheader()
        w.writerows(sorted(sample, key=lambda s: s["segment_id"]))

    meta = {
        "city": args.city,
        "gadm": f"4.1/{args.gadm_country}/level{args.gadm_level}",
        "road_types": ROAD_TYPES,
        "segment_m": SEGMENT_M,
        "frame_segments": len(segments),
        "n_sampled": len(sample),
        "seed": args.seed,
        "radius_m": args.radius_m,
        "overpass_archive": archive.name,
        "overpass_query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    meta_path = out_dir / f"{slug}_frame_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"wrote {sample_path.name} and {meta_path.name}")


if __name__ == "__main__":
    main()
