# What the caste literature says about our signboards

Notes reading the naan-significant results against the classic and
qualitative literature on caste, and what each tradition predicts, explains,
or contests. Numbers referenced are from the README tables (sampled v3 and
grid v2 estimates, and the 1918-1928 directory corpus).

## Dumont: the purity idiom, confirmed for 1925 and broken by 2026

Dumont's *Homo Hierarchicus* (1966) reads caste as a single ideological
order organized by purity and pollution, with jati rank derivative of that
religious axis. His signboard prediction: eateries signal *position in the
purity order*, in the idiom of purity itself, without needing jati names.
The 1925 Madras classified list is nearly a Dumont exhibit: "Hindu
Restaurant" (pure), "Military Hotel" (meat, impure), Vilas/Bhavan
(Sanskritic-vegetarian register), and no caste words. The 2026 data breaks
with him twice. The purity axis has nearly vanished from names. And what
displays now is identity-pride rather than rank: Bengaluru's Gowda military
hotels put a caste name on the *impure* pole of the old classification, a
combination Dumont's scheme cannot produce. (On Bangalore's military-hotel
institution, see the popular record; the form is Vokkaliga/Gowda-associated
non-vegetarian eateries.)

## Srinivas: the surname map is a dominant-caste map

Srinivas gives us two tools. Sanskritization: upward emulation of twice-born
practice, above all vegetarianism. The dominant caste: locally powerful by
land and numbers, not by ritual rank. Our surname geography tracks
dominance, not varna: Gowda (Vokkaliga, dominant in south Karnataka), Reddy
(Andhra), Yadav (the OBC ascendancy of UP and Bihar; 16 of Varanasi's 25
surname matches), Patel, and Meena (east Rajasthan Scheduled Tribe with a
strong public-sector presence; the only SC/ST surname visible anywhere).
Signboards display local confidence. This explains what a ritual-rank
theory cannot: zero Brahmin labels across the North next to a thriving
population of Yadav dhabas. The surviving Brahmin-labeled cafes of
Bengaluru and Mysuru read as sanskritization monetized: a heritage brand
whose content, for the customer, is vegetarian hygiene.

## Marriott and Appadurai: the transaction is gone; the semiotics moved

Marriott (1968) ranked castes by who accepts cooked food from whom;
Appadurai (1981) called food the medium of "gastro-politics," able to
homogenize or heterogenize its transactors. A restaurant anonymizes the
transaction: cash replaces the inter-jati food matrix, and when the cook's
hand stops mattering contractually, the signal on the door loses value.
That is a clean reading of our tenfold collapse. But the heterogenizing
pole did not die; it migrated into diet words. "Pure veg" signage, and the
2024 Zomato pure-veg-fleet controversy, are the modern descendants of
"Hindu Restaurant" - purity semiotics without caste vocabulary. Our
dictionary does not count "pure veg," which means our estimate of identity
signalling is a floor: we measure the caste-worded channel and leave the
diet-worded channel unmeasured.

## Khare: Lucknow's hearth stays home; the trade goes to the Yadavs

Khare's *The Hindu Hearth and Home* (1976) maps the ranked, purity-graded
domestic kitchen of Lucknow's Kanya-Kubja Brahmins. His world predicts that
Brahmin food identity in Lucknow is domestic and that commercial cooking is
franchised out in honorific form. Our Lucknow looks like that: the Brahmin
presence on signs is "Pandit Ji" establishments (the honorific selling
trust and purity), while the volume brand is Yadav, often with the jati's
occupational continuity showing ("Yadav Dudh Dairy & Sweets" - the milk
trade turned eatery).

## Jodhka, Thorat, Parmar: display at the top, concealment at the bottom

Jodhka and Newman (2007) found employers speaking a "hidden language of
caste" - family background as euphemism - while denying caste outright;
Jodhka's work on Dalit enterprise documents concealment of caste markers as
business strategy; Thorat and Attewell's audit study showed the name alone
moves callbacks; Parmar (2020) documents urban Gujaratis changing surnames
to shed stigmatized markers. The joint prediction: the signboard is a
choice, and the choice is asymmetric - display when the name carries
dominance or trust, conceal when it carries stigma. That is precisely our
third finding: upper-caste and merchant surnames at 1-3% against SC/ST
surnames at effectively zero outside Jaipur's Meena. The near-zero is not
evidence of absent Dalit ownership; it is most plausibly the concealment
margin, and it is the result the qualitative literature explains best.

## Damodaran: merchant names are occupational, not purity, claims

*India's New Capitalists* traces which castes entered which businesses,
region by region: mercantile communities first, dominant agrarian castes
later. The halwai (sweet-maker) tradition of the Gupta/Agarwal belt
predicts merchant-surname food branding in the North - and our merchant
column runs 1.0-1.9% in Delhi, Lucknow, Jaipur, and Kolkata against
0.1-0.2% in the South. "Gupta Sweets" is an occupational-caste brand, a
different speech act from "Brahmin's Cafe."

## Conlon and Ray: caste absorbed into cuisine

Conlon (1995) showed Udupi Brahmin hotels teaching a hesitant public to eat
out; Krishnendu Ray's ethnic-restaurateur work shows identity packaged as
cuisine for consumption by outsiders. The South's channel is exactly that
absorption: Udupi, Chettinad, and Andhra are caste and community histories
that survive on signboards as cuisine categories anyone may buy. On this
reading the South did not keep more caste on its signs than the North; it
finished laundering caste into taste earlier.

## What our data cannot say

Branding is not ownership; we observe the sign, not the proprietor. We have
no customer side: whether patrons select on these names is unmeasured. We
do not count "pure veg" and its diet-purity kin, so the modern purity
channel is invisible to the dictionary. And the avoidance-versus-
non-salience question that the README leaves open is, at bottom, not an
observational question.

## What else to bring to bear, ranked

1. **Owner interviews** (n around 30, stratified branded/unbranded by
   city). The single highest-value addition: "how did you choose the name;
   did you consider your community's name" arbitrates avoidance versus
   non-salience directly. Everything else is proxy.
2. **Vegetarian status from Places** (`servesVegetarianFood` field on the
   existing place ids; one cheap field-mask re-query). Operationalizes the
   Dumont/Zomato purity channel: does veg status predict Vilas/Brahmin/
   Pandit naming? Turns "pure veg is the new Hindu Restaurant" into a
   number.
3. **Review text**: do customers mention caste, community, or purity in
   Google reviews of branded versus unbranded places?
4. **A matrimonial-ad contrast corpus**: run the same dictionary over a
   matrimonial sample to quantify the domain contrast the introduction
   asserts (caste everywhere there, nowhere here).
5. **Thacker's directories, 1930s-1950s**: mid-century points between 1925
   and 2025 to date the collapse.
6. **A Dalit-branded eatery press corpus** (they make news because they are
   rare; Shahu Patole's *Dalit Kitchens of Marathwada* as the qualitative
   anchor) to bound the concealment reading.
7. **FSSAI owner-name linkage** (needs an Indian IP): branding conditional
   on owner caste-marked surname - the display-choice estimand.
8. **Price and segment gradients** (Places `priceLevel`): does caste
   branding concentrate downmarket, as the dominance reading predicts?

## Sources

Dumont, *Homo Hierarchicus* (1966). Srinivas on sanskritization and the
dominant caste. Marriott 1968; Appadurai 1981 (both in README refs).
Khare, *The Hindu Hearth and Home* (Vikas, 1976). Conlon 1995. Jodhka &
Newman, "In the Name of Globalisation," EPW 42(41), 2007. Thorat &
Attewell, "The Legacy of Social Exclusion," EPW 2007. Parmar, "Transacting
Caste in Modern Times: Changing Social Identity through Surnames in Urban
Gujarat," CASTE 2020. Damodaran, *India's New Capitalists* (Palgrave,
2008). Ray, *The Ethnic Restaurateur* (Bloomsbury, 2016). Zomato pure-veg
fleet coverage, March 2024 (Al Jazeera, The Leaflet, The Quint). Patole,
*Dalit Kitchens of Marathwada* (2024 translation).
