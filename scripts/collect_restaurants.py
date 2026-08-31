#!/usr/bin/env python3
"""
Collector — Restaurant Catalog for Cities/States (Notebook-safe)
---------------------------------------------------------------

Purpose
  Collect a raw catalog of restaurant names for one or many regions using:
    • Google Places Nearby Search (multi-language, grid-sampled)
    • Overpass/OSM (optional) for cross-check/coverage

Output per run (per region and combined):
  • <base>_<region_id>_raw_collection.jsonl  (lossless raw rows)
  • <base>_<region_id>_raw_collection.csv    (quick spreadsheet)
  • <base>_<region_id>_meta.json             (counters + coverage)

Each raw row includes: place_id, name, source, lang, cell_idx, query center,
place lat/lon (when available), page index, region_id, region_name, timestamp.

Multi-region support
  • Provide one or more --location flags (city name or center/radius), OR
  • Provide a CSV via --locations-csv with columns:
        region_id,region_name,city,center_lat,center_lon,radius_km,grid_step_km
    At least one of (city) OR (center_lat,center_lon,radius_km) must be present.

Dependencies
  pip install googlemaps requests

Notes
  • Nearby Search returns capped, prominence-ranked results per cell. Grid density
    and radius control coverage; there is no "dump everything" endpoint.
  • Set languages like ("kn","en") to improve recall of localized names.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


try:
    import googlemaps  # type: ignore
except Exception:  # pragma: no cover
    googlemaps = None

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

# ------------------------------ Data models ---------------------------------


@dataclass
class Region:
    region_id: str
    region_name: str
    center_lat: float
    center_lon: float
    radius_km: float
    grid_step_km: float = 2.0

    @classmethod
    def from_city(
        cls,
        region_id: str,
        region_name: str,
        city: str,
        *,
        radius_km: float,
        grid_step_km: float,
        gmaps_client: Optional["googlemaps.Client"],
    ) -> "Region":
        if gmaps_client is None:
            raise ValueError(
                "City geocoding requires googlemaps; pass --google-api-key or explicit center"
            )
        ge = gmaps_client.geocode(city)
        if not ge:
            raise ValueError(f"Could not geocode city: {city}")
        loc = ge[0]["geometry"]["location"]
        return cls(
            region_id=region_id,
            region_name=region_name or city,
            center_lat=float(loc["lat"]),
            center_lon=float(loc["lng"]),
            radius_km=radius_km,
            grid_step_km=grid_step_km,
        )


# ------------------------------- Utils --------------------------------------


def grid_cells(center_lat: float, center_lon: float, km_radius: float, km_step: float):
    deg_lat_km = 111.0
    deg_lon_km = 111.0 * math.cos(math.radians(center_lat))
    steps_lat = int(km_radius // km_step)
    steps_lon = int(km_radius // km_step)
    for di in range(-steps_lat, steps_lat + 1):
        for dj in range(-steps_lon, steps_lon + 1):
            yield (
                center_lat + di * (km_step / deg_lat_km),
                center_lon + dj * (km_step / deg_lon_km),
            )


# ----------------------------- Collection -----------------------------------


def collect_places_for_region(
    region: Region,
    *,
    gmaps_client: Optional["googlemaps.Client"],
    languages: Tuple[str, ...] = ("kn", "en"),
    places_radius_m: int = 2000,
    places_sleep_s: float = 2.0,
    max_cells: Optional[int] = 200,
    verbose: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta = {
        "region_id": region.region_id,
        "cells_covered": 0,
        "queries_attempted": 0,
        "requests_made": 0,
        "pages_seen": 0,
        "languages": list(languages),
        "errors": [],
    }
    if gmaps_client is None:
        meta["errors"].append("No googlemaps client")
        return [], meta

    seen: set = set()
    out: List[Dict[str, Any]] = []

    def ingest(
        result: Dict[str, Any],
        lat: float,
        lon: float,
        idx: int,
        lang: str,
        page_idx: int,
    ) -> None:
        for r in result.get("results", []):
            pid = r.get("place_id")
            nm = (r.get("name") or "").strip()
            geom = (r.get("geometry") or {}).get("location") or {}
            if pid and nm and pid not in seen:
                seen.add(pid)
                out.append(
                    {
                        "place_id": pid,
                        "name": nm,
                        "source": "places",
                        "lang": lang,
                        "cell_idx": idx,
                        "query_center_lat": lat,
                        "query_center_lon": lon,
                        "lat": geom.get("lat"),
                        "lon": geom.get("lng"),
                        "page": page_idx,
                        "region_id": region.region_id,
                        "region_name": region.region_name,
                        "collected_at": utc_now_iso(),
                    }
                )

    for idx, (lat, lon) in enumerate(
        grid_cells(
            region.center_lat, region.center_lon, region.radius_km, region.grid_step_km
        )
    ):
        if max_cells is not None and idx >= max_cells:
            # The 2025-08 Chennai run hit this cap (meta shows exactly 200
            # cells), silently truncating coverage — hence the loud warning.
            msg = f"max_cells={max_cells} reached; grid truncated, coverage incomplete"
            meta["errors"].append(msg)
            print(f"⚠️  {region.region_id}: {msg}")
            break
        meta["cells_covered"] += 1
        for lang in languages:
            try:
                if verbose:
                    print(
                        f"· {region.region_id}: cell={idx} lang={lang} near=({lat:.4f},{lon:.4f})"
                    )
                page_idx = 0
                result = gmaps_client.places_nearby(
                    location=(lat, lon),
                    radius=places_radius_m,
                    type="restaurant",
                    language=lang,
                )
                meta["requests_made"] += 1
                ingest(result, lat, lon, idx, lang, page_idx)
                while "next_page_token" in result:
                    time.sleep(places_sleep_s)
                    result = gmaps_client.places_nearby(
                        page_token=result["next_page_token"]
                    )
                    meta["requests_made"] += 1
                    meta["pages_seen"] += 1
                    page_idx += 1
                    ingest(result, lat, lon, idx, lang, page_idx)
                time.sleep(0.3)
            except Exception as e:  # pragma: no cover
                msg = f"Places error @ {region.region_id} cell {idx} lang={lang}: {e}"
                meta["errors"].append(msg)
                if verbose:
                    print("❌", msg)
                time.sleep(0.7)
    meta["queries_attempted"] = meta["cells_covered"] * max(1, len(languages))
    if verbose:
        print(
            f"✅ Places[{region.region_id}]: {len(out)} unique | "
            f"cells={meta['cells_covered']} langs={len(languages)} "
            f"requests={meta['requests_made']} pages={meta['pages_seen']}"
        )
    return out, meta


def collect_overpass_for_region(
    region: Region,
    *,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
    use_area_query: bool = True,
    verbose: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    meta = {
        "region_id": region.region_id,
        "requests_made": 0,
        "url": overpass_url,
        "errors": [],
    }
    if requests is None:
        meta["errors"].append("requests not installed")
        return [], meta

    if use_area_query:
        # Query by region_name as an administrative boundary; escape quotes
        # and backslashes so the name cannot break the Overpass QL string.
        area_name = region.region_name.replace("\\", "\\\\").replace('"', '\\"')
        query = f"""
[out:json][timeout:60];
area["name"="{area_name}"]["boundary"="administrative"]->.a;
(
  node["amenity"="restaurant"](area.a);
  way["amenity"="restaurant"](area.a);
  relation["amenity"="restaurant"](area.a);
);
out center tags;
"""
    else:
        # Fallback: circular bbox around center
        # Compute a simple bbox ~ radius_km around center
        lat, lon = region.center_lat, region.center_lon
        dlat = region.radius_km / 111.0
        dlon = region.radius_km / (111.0 * math.cos(math.radians(lat)))
        s = lat - dlat
        n = lat + dlat
        w = lon - dlon
        e = lon + dlon
        query = f"""
[out:json][timeout:60];
(
  node["amenity"="restaurant"]({s},{w},{n},{e});
  way["amenity"="restaurant"]({s},{w},{n},{e});
  relation["amenity"="restaurant"]({s},{w},{n},{e});
);
out center tags;
"""
    try:
        r = requests.post(overpass_url, data={"data": query}, timeout=120)
        meta["requests_made"] += 1
        r.raise_for_status()
        data = r.json()
        out: List[Dict[str, Any]] = []
        for el in data.get("elements", []):
            tags = el.get("tags") or {}
            name = tags.get("name")
            if not name:
                continue
            plat = el.get("lat")
            plon = el.get("lon")
            if (plat is None or plon is None) and isinstance(el.get("center"), dict):
                plat = el["center"].get("lat")
                plon = el["center"].get("lon")
            out.append(
                {
                    "place_id": f"osm_{el['id']}",
                    "name": name,
                    "source": "osm",
                    "lang": None,
                    "cell_idx": None,
                    "query_center_lat": None,
                    "query_center_lon": None,
                    "lat": plat,
                    "lon": plon,
                    "page": None,
                    "region_id": region.region_id,
                    "region_name": region.region_name,
                    "collected_at": utc_now_iso(),
                }
            )
        if verbose:
            print(f"✅ OSM[{region.region_id}]: {len(out)} restaurants")
        return out, meta
    except Exception as e:  # pragma: no cover
        msg = f"Overpass error @ {region.region_id}: {e}"
        meta["errors"].append(msg)
        if verbose:
            print("❌", msg)
        return [], meta


# ----------------------------- Persistence ----------------------------------


def save_raw_for_region(
    raw_list: List[Dict[str, Any]], basepath: str, region_id: str
) -> Tuple[str, str]:
    path_jsonl = f"{basepath}_{region_id}_raw_collection.jsonl"
    path_csv = f"{basepath}_{region_id}_raw_collection.csv"
    with open(path_jsonl, "w", encoding="utf-8") as f:
        for r in raw_list:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cols = [
        "place_id",
        "name",
        "source",
        "lang",
        "cell_idx",
        "query_center_lat",
        "query_center_lon",
        "lat",
        "lon",
        "page",
        "region_id",
        "region_name",
        "collected_at",
    ]
    with open(path_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in raw_list:
            w.writerow([r.get(c) for c in cols])
    return path_jsonl, path_csv


def save_meta(meta: Dict[str, Any], basepath: str, region_id: str) -> str:
    path_meta = f"{basepath}_{region_id}_meta.json"
    with open(path_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return path_meta


# ------------------------------- CLI/Notebook --------------------------------


def parse_locations_csv(
    path: str,
    *,
    gmaps_client: Optional["googlemaps.Client"],
    default_radius_km: float,
    default_grid_step_km: float,
) -> List[Region]:
    out: List[Region] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rid = (row.get("region_id") or f"r{i}").strip()
            rname = (row.get("region_name") or "").strip() or rid
            city = (row.get("city") or "").strip()
            radius_km = float(row.get("radius_km") or default_radius_km)
            grid_step_km = float(row.get("grid_step_km") or default_grid_step_km)
            lat = row.get("center_lat")
            lon = row.get("center_lon")
            if city:
                out.append(
                    Region.from_city(
                        rid,
                        rname,
                        city,
                        radius_km=radius_km,
                        grid_step_km=grid_step_km,
                        gmaps_client=gmaps_client,
                    )
                )
            elif lat and lon:
                out.append(
                    Region(rid, rname, float(lat), float(lon), radius_km, grid_step_km)
                )
            else:
                raise ValueError(f"Row {i}: need either city or center_lat/center_lon")
    return out


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect restaurant names (Google Places + OSM) for one or more regions"
    )
    # Regions
    parser.add_argument(
        "--location",
        action="append",
        nargs=5,
        metavar=("region_id", "region_name", "center_lat", "center_lon", "radius_km"),
        help="Add a region by center/radius (can be repeated)",
    )
    parser.add_argument(
        "--locations-csv",
        type=str,
        default=None,
        help="CSV with region_id,region_name,city,center_lat,center_lon,radius_km,grid_step_km",
    )
    parser.add_argument(
        "--city",
        action="append",
        nargs=3,
        metavar=("region_id", "region_name", "city_name"),
        help="Add a region by city name (requires Google geocoding",
    )

    # Places
    parser.add_argument("--use-google-places", action="store_true")
    parser.add_argument(
        "--google-api-key", type=str, default=os.environ.get("GOOGLE_API_KEY")
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=["kn", "en"],
        help="Languages to query, e.g., kn en",
    )
    parser.add_argument("--grid-step-km", type=float, default=2.0)
    parser.add_argument("--places-radius-m", type=int, default=2000)
    parser.add_argument("--places-sleep-s", type=float, default=2.0)
    parser.add_argument("--max-cells", type=int, default=200)

    # OSM
    parser.add_argument("--use-overpass", action="store_true")
    parser.add_argument(
        "--overpass-url", type=str, default="https://overpass-api.de/api/interpreter"
    )

    # Output
    parser.add_argument(
        "--basepath",
        type=str,
        default=f"restaurants_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    # Build regions list
    gmaps_client = (
        googlemaps.Client(key=args.google_api_key)
        if (args.use_google_places and args.google_api_key and googlemaps)
        else None
    )
    regions: List[Region] = []
    if args.locations_csv:
        regions += parse_locations_csv(
            args.locations_csv,
            gmaps_client=gmaps_client,
            default_radius_km=20.0,
            default_grid_step_km=args.grid_step_km,
        )
    if args.location:
        for rid, rname, lat, lon, rad in args.location:
            regions.append(
                Region(
                    rid,
                    rname,
                    float(lat),
                    float(lon),
                    float(rad),
                    grid_step_km=args.grid_step_km,
                )
            )
    if args.city:
        for rid, rname, city in args.city:
            regions.append(
                Region.from_city(
                    rid,
                    rname,
                    city,
                    radius_km=20.0,
                    grid_step_km=args.grid_step_km,
                    gmaps_client=gmaps_client,
                )
            )

    if not regions:
        # default: Bengaluru center
        regions = [
            Region(
                "blr",
                "Bengaluru",
                12.9716,
                77.5946,
                22.0,
                grid_step_km=args.grid_step_km,
            )
        ]

    languages = tuple(args.languages)

    for r in regions:
        raw_all: List[Dict[str, Any]] = []
        if args.use_google_places:
            raw_p, meta_p = collect_places_for_region(
                r,
                gmaps_client=gmaps_client,
                languages=languages,
                places_radius_m=args.places_radius_m,
                places_sleep_s=args.places_sleep_s,
                max_cells=args.max_cells,
                verbose=args.verbose,
            )
            meta_p.update({"region_name": r.region_name})
            save_meta(meta_p, args.basepath, r.region_id)
            raw_all += raw_p
        if args.use_overpass:
            raw_o, meta_o = collect_overpass_for_region(
                r, overpass_url=args.overpass_url, verbose=args.verbose
            )
            meta_o.update({"region_name": r.region_name})
            save_meta(meta_o, args.basepath, r.region_id + "_osm")
            raw_all += raw_o
        p_jsonl, p_csv = save_raw_for_region(raw_all, args.basepath, r.region_id)
        if args.verbose:
            print(f"Saved: {p_jsonl} and {p_csv}")


if __name__ == "__main__":
    main()
