# Caste and community in Indian restaurant names

Caste shows up in many corners of Indian life, from surnames to matrimonial
ads. We asked whether it also shows up in commercial branding, where the
audience is everyone: do restaurants put caste in their names? Mostly, no. Among 14,907 restaurants collected
from Google Places and OpenStreetMap for Bengaluru, Chennai, and Mysuru in
August 2025, explicit caste and community labels (Brahmin's Veg Cafe, Iyer
Mess, Sree Gupta Bhavan) appear in under 1% of names in every city, and
caste-linked surnames (Gowdru Military Hotel, Reddy's Family Dhaba) in 0.1%
to 1.1%. Identity reaches meaningful rates only in a softer
form: regional and cuisine identities (Udupi, Kerala, Punjabi, Mysore-style)
bring the total with any confirmed caste or community reference to 4.3% in
Bengaluru, 1.4% in Chennai, and 5.7% in Mysuru. Roughly one urban restaurant
in twenty brands itself with an identity, and when it does, it names a
cuisine region far more often than a caste.

Chennai's low figure is partly an artifact of our dictionary, which tilts
toward Karnataka communities. A model-based screen of unmatched names (below)
found about 2% of Chennai's names carry references the dictionary lacks,
mostly Chettinad cuisine and Tamil surnames such as Pandian; the corrected
any-reference rate for Chennai is roughly 3.3%.

## Data

Restaurant names come from two sources, collected 2025-08-22/23:

1. **Google Places** Nearby Search over a lat/lon grid covering each city
   (2 km steps, `type=restaurant`, queried in Kannada and English), paged to
   exhaustion per cell.
2. **OpenStreetMap** via one Overpass query per city for
   `amenity=restaurant` within the administrative boundary.

Unique restaurants after dedup and cross-source linkage: Bengaluru 7,770,
Chennai 4,962, Mysuru 2,175. Rows from the two sources describing the same
restaurant (token Jaccard ≥ 0.5 within 200 m) count once; same-name pairs
farther apart are chain branches and stay separate. The raw collections for
Bengaluru and Mysuru were reconstructed from the committed matches files
(`scripts/reconstruct_raw.py`); the method round-trips exactly on Chennai,
where the original file survives.

## Method

Matching is exact word-boundary regex over a fixed dictionary of 31 labels in
four groups: upper-caste labels (Brahmin, Iyer, Iyengar, GSB, ...), merchant
communities (Jain, Marwari, Agarwal, Gupta, ...), regional or cuisine
identities (Udupi, Coorg, Kerala, Punjabi, Mysore, ...), and caste-linked
surnames (Gowda, Shetty, Reddy, Naidu, Bhat, ...). Each label carries
hand-curated spelling variants only (bhat/bhatt, kamath/kamat, udupi/udipi).
Names in Kannada, Tamil, Telugu, Malayalam, or Devanagari script are
transliterated to Latin first (IAST via `indic-transliteration`, diacritics
stripped), which leaves only 10 of 14,907 names unscorable.

Matching is exact only: fuzzy matching at edit distance 1 on terms this
short mostly manufactures false positives ("chats" matches Bhat, "Sai"
matches Pai), so spelling variation is handled by the curated variant lists
instead.

Every dictionary match was then adjudicated by a local open-weights LLM
(Qwen3-8B via Ollama, temperature 0, so the step re-runs for free). The
adjudication is used asymmetrically, because it is reliable on one question
and not the other:

* For regional matches the model judges usage: is the word branding
  ("Kerala Corner") or incidental address text ("Domino's Pizza | JC Nagar,
  Mysore")? On inspection its calls were consistently right, and they remove
  4.9% of regional matches in Bengaluru, 12% in Chennai, and 34% in Mysuru,
  where restaurants routinely append the city to their listing.
* For the caste groups the model was asked the same question but answered a
  different, factual one, and got it wrong: all 16 of its rejections were
  real caste-linked surnames or communities (Kamat, Pai, Rao, GSB, Marwadi),
  rejected with reasons like "kamat not a caste name". Those vetoes are
  ignored. Instead, every distinct matched name in the caste groups (165 of
  them) was inspected by hand; none is a lookalike.

The same model screened 500 unmatched names per city for references the
dictionary lacks, and each hit had to survive a second, targeted question.
Confirmed misses: 1 in Bengaluru (0.2%), 10 in Chennai (2.0%), 6 in Mysuru
(1.2%). The Chennai misses are systematic, not noise: four are Chettinad and
the rest are mostly Tamil surnames (Pandian, Veerasamy). The screen has noise
of its own in both directions (it counted "Devegowda Circle", which is an
address, and never flagged Andhra, see below), so read these rates as rough.

## Results

Share of restaurant names with a confirmed reference, by group and city
(Wilson 95% CIs in `data/final_estimates_2026_08_30.csv`):

| Group | Bengaluru (n=7,770) | Chennai (n=4,962) | Mysuru (n=2,175) |
|---|---|---|---|
| Regional / cuisine | 2.8% | 0.6% | 4.3% |
| Caste-linked surname | 1.1% | 0.1% | 0.7% |
| Upper-caste label | 0.4% | 0.1% | 0.6% |
| Merchant community | 0.1% | 0.5% | 0.2% |
| **Any of the above** | **4.3%** | **1.4%** | **5.7%** |
| Any, corrected for dictionary misses | 4.5% | 3.3% | 6.9% |

Within the groups, the leading labels are Udupi (132 restaurants in
Bengaluru), Karnataka place names in Mysuru (52 confirmed, down from 103
flagged once address matches are dropped), Gowda (27) and Reddy (18) in
Bengaluru, Gupta (15) and Jain (8) in Chennai, and Brahmin (22 in Bengaluru,
9 in Mysuru, 0 in Chennai). Per-label counts are in
`data/analysis_2026_08_30_*_label_counts.csv`.

## Interpretation

The rarity is the finding, and two readings fit it that the design cannot
separate. Restaurants
sell to broad publics, so an explicit caste label narrows the market, and
owners who want to signal identity may reach for regional-cuisine codes that
carry community lineage without naming it ("Udupi" rather than "Brahmin").
Or caste may simply not be a salient axis for branding food service in these
cities. The internal contrast, regional-cuisine branding running four to seven
times ahead of upper-caste labels in every city, is consistent with the
first reading but does not establish it.

The classic literature makes the rarity more striking. In the classical
account the cook's caste was the point: castes were ranked in part by whose
cooked food they would accept (Marriott 1968), food from Brahmin kitchens
was acceptable to nearly everyone, and early public dining in Indian cities
was organized around exactly this, with eating houses sorted by caste and
region and "Brahmin" or "Udupi Brahmin" on the board serving as a purity
guarantee that let hesitant middle-class Hindus eat out at all (Conlon
1995). A century later the label that once did that work survives on 22
signboards in Bengaluru, while its descendant, Udupi as the name of a
cuisine rather than a guarantee, is the single largest category in the data.

The rarity is measured, not assumed: every match was verified (address text
vetoed, every distinct caste-group name inspected), missed names were
screened for, and the dictionary was frozen before results were inspected.

## What the numbers rest on

The denominator is restaurants visible on two platforms, not all
restaurants. Places returns prominence-ranked results per grid cell and the
grid was capped at 200 cells, which truncated Chennai's coverage (its
collection meta shows the cap was hit). OSM is volunteer coverage. A
capture-recapture estimate of the true restaurant count is computed but not
credible (the two sources overlap too little and match too imperfectly for
Chapman's assumptions), so the observed union is the denominator throughout.

Chennai is measured worse than the other two cities. The collector queried
in Kannada and English but never Tamil, its OSM pull is six times thinner
than Bengaluru's, and the dictionary undercovers Tamil communities.
Cross-city comparisons involving Chennai should lean on the corrected row.

The dictionary has known gaps. Andhra ("Andhra Ruchulu", 94 unmatched names
contain the token) is regional branding the dictionary omits and the screen
failed to flag. Chettinad is the largest confirmed Chennai gap. The
dictionary was frozen before results were inspected and deliberately not
patched afterward.

A name is a weak proxy. "Udupi" on a signboard signals a cuisine tradition
with Brahmin roots, not the owner's caste; a surname signals the owner's
family, not the clientele. The estimand is branding, not ownership
demography.

Own-city references cut both ways. "Mysore Cafe" in Mysuru counts as
regional branding when the model judges it branding rather than address
text. To exclude own-city place names entirely, drop the `mysore` term from
the Mysuru rows; the regional rate there falls from 4.3% to 1.9%.

## Reproducing

```bash
pip install -r requirements.txt

# 1. Rebuild blr/mys raw collections from the committed matches files
python scripts/reconstruct_raw.py

# 2. Dictionary matching, dedup, per-region and combined outputs
python scripts/analyze_caste_branding.py \
    --inputs 'data/restaurants_2025_08_22_*_raw_collection.jsonl' \
    --basepath data/analysis_2026_08_30

# 3. LLM adjudication (needs Ollama with qwen3:8b pulled; ~75 min on an M4)
python scripts/adjudicate_matches.py \
    --basepath data/analysis_2026_08_30 \
    --out data/adjudication_2026_08_30.jsonl

# 4. Final corrected estimates
python scripts/final_estimates.py \
    --basepath data/analysis_2026_08_30 \
    --adjudication data/adjudication_2026_08_30.jsonl \
    --out data/final_estimates_2026_08_30.csv
```

Step 3 is checkpointed; re-running resumes. Collecting fresh data needs a
Google Places key: see `python scripts/collect_restaurants.py --help`.

## Files

| Path | What it is |
|---|---|
| `scripts/collect_restaurants.py` | Places grid + Overpass collector |
| `scripts/reconstruct_raw.py` | rebuilds blr/mys raws from matches files |
| `scripts/analyze_caste_branding.py` | dictionary, transliteration, linkage, prevalence |
| `scripts/adjudicate_matches.py` | LLM verification of matches and screen of non-matches |
| `scripts/final_estimates.py` | merges verdicts into the corrected estimates |
| `data/restaurants_2025_08_22_*` | raw collections and collection meta |
| `data/analysis_2026_08_30_*` | matches, summaries, per-label counts |
| `data/adjudication_2026_08_30.jsonl` | every LLM verdict |
| `data/final_estimates_2026_08_30.csv` | the headline table with CIs |

## References

Conlon, Frank F. 1995. "Dining Out in Bombay." In *Consuming Modernity:
Public Culture in a South Asian World*, ed. Carol A. Breckenridge, 90-127.
Minneapolis: University of Minnesota Press.

Marriott, McKim. 1968. "Caste Ranking and Food Transactions: A Matrix
Analysis." In *Structure and Change in Indian Society*, eds. Milton Singer
and Bernard S. Cohn, 133-171. Chicago: Aldine.
