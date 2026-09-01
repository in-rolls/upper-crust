# Caste and community in Indian restaurant names

Caste shows up in many corners of Indian life, from surnames to matrimonial
ads. We asked whether it also shows up in commercial branding, where the
audience is everyone: do restaurants put caste in their names? To answer,
we drew probability samples of restaurants in eight districts spanning
North and South (21,719 names, 2026), swept three southern cities on Google
Places and OpenStreetMap (14,907 names, 2025), matched every name against a
fixed dictionary of caste and community terms with every match verified,
and hand-coded eating houses from digitized 1920s trade directories.

Four findings. First, putting caste itself in the name is rare everywhere:
explicit caste and community labels (Brahmin's Veg Cafe, Iyer Mess) top out
at 0.8% of names, and outside Karnataka they are near zero. Second,
identity branding more broadly runs 2 to 8% of names, and its form splits
by region: the South names a cuisine region (Udupi, Andhra, Chettinad); the
North names the owner (Yadav, Pandit, Mishra, Gupta), and its
regional-cuisine branding is marginal. Third, the signboard mirrors the
hierarchy: surnames informative of Scheduled Caste or Tribe membership are
essentially absent everywhere except Jaipur, where the Meena community
(a Rajasthan Scheduled Tribe) appears on about 0.4% of signs, against 1 to
3% for upper-caste and merchant surnames. Fourth, this is a collapse, not a
constant: among Indian-run eating houses in the 1925 Madras directory,
identity and purity branding was the norm, fifteen of eighteen
establishments. The caste word was rare even then. What changed is how
often any identity signal is sent.

## Data and method in outline

The primary design is a probability sample. For each of eight districts
(Bengaluru, Chennai, Mysuru, Delhi, Kolkata, Lucknow, Jaipur, Varanasi) we
drew 400 street segments at random (seed 42) from all OpenStreetMap roads
inside the district's GADM boundary and queried Google Places for
restaurants at each segment midpoint (300 m radius, nearest first).
Segments are the clusters for bootstrap confidence intervals, and
street-density weights check for oversampling of dense neighborhoods (the
largest shift is 1.2 points, in the smallest sample; most are far under
half a point). The 2025 grid
sweeps of the three southern cities, which also pull OpenStreetMap
listings, serve as a robustness set: where the designs overlap they agree
to within 0.3 points.

A name counts as caste- or community-coded when it contains a term from a
fixed dictionary of 40 labels in four groups: upper-caste labels (Brahmin,
Iyer, Iyengar, GSB), merchant communities (Jain, Marwari, Agarwal,
Chettiar), regional and cuisine identities (Udupi, Chettinad, Andhra,
Kerala, Punjabi), and caste-linked surnames (Gowda, Shetty, Reddy, Yadav,
Mishra, Chatterjee). Matching is exact word-boundary regex over
hand-curated spelling variants; non-Latin scripts are transliterated first.
Every match was then verified: a local LLM judges whether a regional term
is branding or incidental address text, every distinct caste-group match
was inspected by hand, and fourteen address or homograph artifacts are
removed by an auditable exclusion list. Missed names are measured by
screening random samples of unmatched names. The historical corpus is 83
eating houses hand-coded from the Asylum Press directories of Madras and
Southern India (1918 to 1928), each entry coded by segment (Indian or
European) and traceable to its OCR line.

## Results

Share of names with a confirmed caste or community reference, sampled
districts, 2026 (cluster-bootstrap 95% CIs in
`data/sampled_estimates_v3_*.csv`):

| District | n | Any (95% CI) | Regional / cuisine | Surname | Merchant | Upper-caste |
|---|---|---|---|---|---|---|
| Mysuru | 904 | 7.6% [5.9, 9.5] | 6.2% | 0.8% | 0.1% | 0.8% |
| Lucknow | 1,855 | 5.4% [4.4, 6.6] | 0.3% | 3.2% | 1.9% | 0 |
| Bengaluru | 3,447 | 5.0% [4.2, 5.8] | 2.8% | 1.8% | 0.2% | 0.2% |
| Delhi | 4,009 | 4.4% [3.8, 5.1] | 1.5% | 1.5% | 1.4% | 0 |
| Varanasi | 940 | 4.1% [2.8, 5.7] | 0.1% | 2.6% | 1.4% | 0.1% |
| Jaipur | 1,771 | 3.7% [2.7, 4.7] | 0.6% | 2.1% | 1.0% | 0 |
| Chennai | 5,025 | 3.0% [2.5, 3.6] | 2.5% | 0.4% | 0.2% | 0.04% |
| Kolkata | 3,768 | 2.4% [1.9, 3.0] | 0.5% | 1.0% | 0.9% | 0 |

The totals sit in one band; the composition splits North from South. In the
South, branding names a cuisine region: Udupi and Andhra in Bengaluru,
Chettinad and Andhra in Chennai, and in Mysuru the Karnataka place names
that dominate its regional column. In the North, branding names the owner:
surnames and merchant communities carry Lucknow, Varanasi, and Jaipur
almost entirely, and regional-cuisine branding is marginal. Delhi, the
migrant metropolis, is the one city where all three channels run evenly.
Explicit upper-caste labels exist only in Karnataka (Brahmin: 22
restaurants in the Bengaluru grid sweep, 9 in Mysuru) and are zero in all
five northern and eastern districts. Varanasi, the religious city, has the
most surname branding, and it belongs not to Brahmins but to Yadavs (16 of
its 25 surname matches), with "Pandit Ji" establishments the runner-up
across the North.

The other end of the hierarchy is nearly silent. Matching all sampled names
against the 135 surnames most informative of Scheduled Caste or Tribe
membership (SECC-weighted, from the companion last-name-basis repo) and
hand-reviewing every hit leaves Meena in Jaipur (around 0.4% of signs, a
Rajasthan Scheduled Tribe with a strong public-sector presence) and one
Tamang, with effectively zero elsewhere.

The 2025 grid sweeps of the southern cities give the same picture
(dictionary v2; Wilson 95% CIs in `data/final_estimates_2026_08_31_v2.csv`):

| City (grid, 2025) | n | Any | Regional | Surname | Merchant | Upper-caste |
|---|---|---|---|---|---|---|
| Mysuru | 2,175 | 6.2% | 4.5% | 0.9% | 0.2% | 0.6% |
| Bengaluru | 7,770 | 5.3% | 3.7% | 1.1% | 0.1% | 0.4% |
| Chennai | 4,962 | 3.2% | 2.2% | 0.5% | 0.5% | 0.1% |

A century ago the picture was inverted. Among the 18 Indian-run eating
houses in the complete 1925 Madras classified list
(`data/historical/eating_houses_1918_1928.csv`), 15 carried an identity or
purity marker: five "Hindu Restaurant" labels, seven Vilas/Bhavan names,
one Arya, one "Military" (the era's non-vegetarian marker). Identity
branding among Indian establishments has fallen roughly tenfold. The caste
word itself was rare in both eras: none of those 18 names carries one, and
the whole 83-establishment corpus has two (M. Sankara Iyer's hotel, Madras
1918; Brahmin Bakery, Salem 1925).

## Interpretation

The rarity of the caste word is the finding, and two readings fit it that
the design cannot separate. Restaurants sell to broad publics, so an
explicit caste label narrows the market, and owners who want to signal
identity may reach for codes that carry community lineage without naming it:
a cuisine region in the South ("Udupi" rather than "Brahmin"), a surname or
an honorific in the North ("Pandit Ji" rather than "Brahmin"). Or caste may
simply not be a salient axis for branding food service. That the channel
differs by region while the total stays in a narrow band is consistent with
the first reading but does not establish it.

The classic literature says the cook's caste was once the point: castes
were ranked in part by whose cooked food they would accept (Marriott 1968),
and early public dining was organized around purity, with "pure" vegetarian
restaurants easing hesitant diners into eating out (Conlon 1995). The
directories bear that out, with a twist: the purity signal on 1920s
signboards was religious and dietary ("Hindu", "Military", Vilas/Bhavan),
not caste. The signal has always ridden on something adjacent to caste;
what collapsed is how often any signal is sent at all.

The rarity is measured, not assumed: every match was verified, missed names
were screened for, and each dictionary version was frozen before its
results were inspected.

## Method details

**Two collections, and why.** The 2025 sweeps laid a 2 km query grid over
each southern city (Google Places Nearby Search, Kannada and English) plus
one Overpass query for OpenStreetMap restaurants; cross-source rows for the
same restaurant are linked by token Jaccard ≥ 0.5 within 200 m and count
once. That design had two defects we could not repair in place: Chennai was
queried in Kannada but never Tamil, and a 200-cell cap truncated its grid.
The 2026 sampled collections fix both and extend coverage north: random
street segments from a frozen OSM frame (raw Overpass responses archived in
`data/sampling/`), one English-language Places API (New) query per segment.
English is deliberate: the API returns the same places regardless of query
language (verified in a pilot), and the common transliteration scheme for
plain Tamil is unreliable (it renders Chettinad as "jhedhdhinadhu"), so
Latin-script names are the ones the dictionary can score. A capture
recapture estimate of the true restaurant count was computed and rejected:
the two sources overlap too little and match too imperfectly for Chapman's
assumptions.

**Dictionary versions.** v1 leaned toward Karnataka communities. A
model-based screen of unmatched names estimated that missed terms, mostly
Chettinad and Tamil surnames, would raise Chennai's rate from 1.4% to about
3.3%; v2 added those terms, frozen before its results were seen, and the
direct remeasurement gave 3.2%, validating the screen. v3, frozen before
the northern and eastern collections, added UP/Bihar Brahmin surnames
(Mishra, Tiwari, Pandey, Dubey, Shukla), Kayastha, and Bengali caste
surnames; it roughly doubled Lucknow's surname rate (1.8% to 3.3%),
confirming that northern upper-caste identity travels by surname, not
label. Pan-caste names (Singh, Das, Verma, Kumar) are excluded throughout.
Tables above use v3 for the sampled districts and v2 for the grid; v3
changes the southern numbers negligibly (Bengaluru 4.96% to 5.02%).

**Verification.** Every dictionary match was adjudicated by a local
open-weights LLM (Qwen3-8B via Ollama, temperature 0, so the step re-runs
for free), used asymmetrically because it is reliable on one question and
not the other. For regional terms it judges usage, branding ("Kerala
Corner") versus address text ("Domino's Pizza | JC Nagar, Mysore"), and its
calls were consistently right on inspection, removing a third of Mysuru's
regional matches. For caste groups it answered a factual question wrongly
(all 16 of its rejections were real caste surnames such as Kamat and Pai,
rejected with reasons like "kamat not a caste name"), so there the
dictionary match stands, validated by hand inspection of every distinct
matched name; the fourteen address and homograph artifacts that inspection
caught (Mukherjee Nagar is a Delhi locality, "Mitra Da Dhaba" is Punjabi
for friend's dhaba, "Datta" in the South is the deity) are removed via
`data/match_exclusions.csv`, one reason per row. Matching is exact only:
fuzzy matching at edit distance 1 on terms this short mostly manufactures
false positives ("chats" matches Bhat, "Sai" matches Pai). The miss-rate
screens sampled roughly 500 unmatched names per city, each hit surviving a
second, targeted question.

**Sampling mechanics.** Frames are all OSM roads (trunk through
residential) inside each district's GADM 4.1 boundary, split into ~500 m
segments (9,913 in Kolkata, 181,435 in Bangalore district); samples are
shuffle-prefix draws, so a larger n with the same seed nests the smaller
one. Queries rank by distance with a 20-result cap; a capped query is an
adaptively smaller circle, not a prominence-ranked one, and the capped
share is recorded in each run's meta file. All eight districts cost about
4,500 of the 5,000 free monthly Places calls; every run finished with zero
API errors.

## What the numbers rest on

The denominator is restaurants visible on these platforms, not all
restaurants, and Places' restaurant type is loose in India (tea stalls and
the odd non-restaurant appear), diluting every denominator equally. The
sampled estimand is the district, so Mysuru and Varanasi include rural
blocks and are smaller universes than their city cores. A name is a weak
proxy: "Udupi" on a signboard signals a cuisine tradition with Brahmin
roots, not the owner's caste, and a surname signals the owner's family, not
the clientele; the estimand is branding, not ownership demography. Own-city
references cut both ways: "Mysore Cafe" in Mysuru counts as branding when
the model judges it so; excluding the own-city term entirely drops Mysuru's
grid regional rate from 4.5% to 1.9%. The historical corpus is small and
skewed toward establishments prominent enough to be listed; its OCR is
rough, which is why every coded entry carries its source line.

## Reproducing

```bash
pip install -r requirements.txt

# Sampled pipeline (primary): frame -> collect -> match -> adjudicate -> estimate
python scripts/sample_frame.py --city Chennai --n 400 --seed 42
python scripts/collect_restaurants.py --use-google-places --api new \
    --location maa2 Chennai 13.0827 80.2707 15 --languages en \
    --places-radius-m 300 --points-csv data/sampling/chennai_segments_n400_seed42.csv \
    --basepath data/restaurants_2026_08_31        # needs GOOGLE_API_KEY
python scripts/analyze_caste_branding.py \
    --inputs data/restaurants_2026_08_31_maa2_raw_collection.jsonl \
    --basepath data/analysis_2026_08_31_s3
python scripts/adjudicate_matches.py \
    --basepath data/analysis_2026_08_31_s3 \
    --out data/adjudication_2026_08_30.jsonl      # needs Ollama + qwen3:8b
python scripts/sampled_estimates.py \
    --matches data/analysis_2026_08_31_s3_region_maa2_matches.jsonl \
    --adjudication data/adjudication_2026_08_30.jsonl \
    --sample-csv data/sampling/chennai_segments_n400_seed42.csv \
    --out data/sampled_estimates_v3_maa2.csv

# SC/ST-informative surname check (needs ../last-name-basis)
python scripts/scst_signal.py \
    --lookup ../last-name-basis/out/tab/per_name_secc_weighted.parquet \
    --inputs 'data/restaurants_2026_08_31_*_raw_collection.jsonl'

# Grid pipeline (2025 data): rebuild raws, match, adjudicate, estimate
python scripts/reconstruct_raw.py
python scripts/analyze_caste_branding.py \
    --inputs 'data/restaurants_2025_08_22_*_raw_collection.jsonl' \
    --basepath data/analysis_2026_08_31_v2
python scripts/final_estimates.py \
    --basepath data/analysis_2026_08_31_v2 \
    --adjudication data/adjudication_2026_08_30.jsonl \
    --fn-sample-basepath data/analysis_2026_08_30 \
    --out data/final_estimates_2026_08_31_v2.csv

# Historical directories
python scripts/historical_directories.py --download
```

Adjudication is checkpointed; re-running resumes.

## Files

| Path | What it is |
|---|---|
| `scripts/sample_frame.py` | reproducible street-segment sampling frame |
| `scripts/collect_restaurants.py` | Places (grid or sampled points) + Overpass collector |
| `scripts/analyze_caste_branding.py` | dictionary (v3), transliteration, linkage, prevalence |
| `scripts/adjudicate_matches.py` | LLM verification of matches, screen of non-matches |
| `scripts/sampled_estimates.py` | cluster-bootstrap estimates for sampled collections |
| `scripts/final_estimates.py` | adjudicated estimates for the grid collections |
| `scripts/scst_signal.py` | SC/ST-informative surname check |
| `scripts/reconstruct_raw.py` | rebuilds 2025 blr/mys raws from matches files |
| `scripts/historical_directories.py` | fetches 1918-1928 directories, extracts hotel sections |
| `data/sampling/` | eight district frames, seed-42 samples, frozen OSM archives |
| `data/restaurants_2026_08_31_*` | sampled collections (eight districts) |
| `data/restaurants_2025_08_22_*` | grid collections (three cities) and meta |
| `data/sampled_estimates_v3_*.csv` | Table 1, with bootstrap CIs |
| `data/final_estimates_2026_08_31_v2.csv` | grid table, with Wilson CIs (v1: `..._2026_08_30.csv`) |
| `data/match_exclusions.csv` | the fourteen removed address/homograph matches, with reasons |
| `data/analysis_*` | matches, summaries, per-label counts (all dictionary versions) |
| `data/adjudication_2026_08_30.jsonl` | every LLM verdict |
| `data/historical/eating_houses_1918_1928.csv` | hand-coded 1918-1928 eating houses |

## References

Conlon, Frank F. 1995. "Dining Out in Bombay." In *Consuming Modernity:
Public Culture in a South Asian World*, ed. Carol A. Breckenridge, 90-127.
Minneapolis: University of Minnesota Press.

Marriott, McKim. 1968. "Caste Ranking and Food Transactions: A Matrix
Analysis." In *Structure and Change in Indian Society*, eds. Milton Singer
and Bernard S. Cohn, 133-171. Chicago: Aldine.
