#!/usr/bin/env python3
"""
pii_table_en.py -- generate a balanced synthetic PII value table for
English-language Belgian clinical-report templates (international/expat
patient population, NOT UK/US-native).

Fork of personal_finetune/french/pii_table_fr.py (not the Dutch original --
the French file already carries every structural bugfix found during that
build: DX_NUMERIC_2..9, DX_CNK/DX_CNK_2, DX_BELAC, and the corrected
month-name/floor-variant/URL-path locations). See
personal_finetune/english/HANDOFF.md for the full Dutch->French build
history this fork deliberately avoids re-discovering.

What changed vs. the French fork, and why
------------------------------------------
Belgian-STRUCTURAL logic is UNCHANGED (national, not language-specific):
    make_insz, make_riziv, make_iban_be, luhn_card, fmt_insz, fmt_riziv,
    fmt_iban, make_phone, AGE_BANDS, NOISE_OPS, inject_noise, the
    MERGED/SPLIT/FLAT9/SUBJECT label-scheme dicts, render(), audit().

Annotation label taxonomy is DELIBERATELY IDENTICAL to Dutch/French (user
decision, 2026-08-18): the JSON span label stays "INSZ"/"RIZIV"/etc, same
as every other language track. This is independent of the in-document
PROSE, which uses the researched-correct English administrative terms
(see DEMO_TEMPLATE and the translated template bank) -- exactly the same
relationship French has (label stays "INSZ" while the letter text reads
"NISS").

Locked-in decisions this fork encodes (resolved via explicit user Q&A
before this file was written, mirroring how "Belgian French not
France-French" had to be confirmed before the French fork started):
  - Geography: NATIONALLY DISTRIBUTED, not concentrated on one region --
    BELGIAN_CITIES merges the Dutch track's Flemish city table with the
    French track's Walloon+Brussels table (both already research-grounded
    in their own files) rather than re-deriving population weights from
    scratch. Street naming is REGION-AWARE (make_street() dispatches to
    the Dutch compound-word style or the French "type + de/du" style
    depending on the sampled city's region) -- there is no "English
    street name" convention, so real regional Belgian names are reused
    unchanged, exactly as decided.
  - NAMES: rebuilt entirely around the REAL demographic reality of who is
    actually treated in English in Belgium -- an expat/international
    community (UK/Ireland, US, other-EU staff using English as lingua
    franca, Anglophone Africa/Asia), NOT the native-population-plus-
    immigrant-minority framing French/Dutch use (there is no native
    English-speaking linguistic region in Belgium). No official Belgian
    census breaks down "English-speaking resident population by origin"
    the way Statbel's per-region data let French/Dutch weight WALLOON_
    CITIES/CITIES precisely -- these weights are a REASONED ESTIMATE,
    flagged honestly here rather than presented as Statbel-sourced (same
    honesty standard the French track already applied to its own
    central_african weight).
  - SPECIALTIES/DIAGNOSES: British/international spelling and
    terminology (locked-in decision), e.g. "anaemia" not "anemia",
    "Gynaecology"/"Orthopaedics" not the American spellings, English
    eponym convention (possessive 's: "Crohn's disease") rather than
    French's "maladie de X".
  - HOSPITAL_*: merged from both existing tracks' already-verified real
    institution lists (Dutch AZ/UZ network + French CHU/CHR/Clinique
    network) -- nationally distributed means English-language documents
    plausibly come from either.
  - DISTRACTORS["municipality_homograph"]: fresh English-specific
    research, same honest-small-list principle the French track applied
    (4 entries, not a forced 9) -- real Belgian place names that also
    happen to be ordinary English words: Spa (the town that gave English
    the word "spa"), Peer (Limburg town / English "a peer"), Ways
    (Genappe hamlet / English "ways"), Marche (Marche-en-Famenne /
    English "march", month or gait -- a genuinely different collision
    class from French's own Marche=gait reading of the same town).
  - DISTRACTORS["code_switch"]: for ENGLISH documents, code-switching
    means French or Dutch clinical phrases embedded in English prose
    (realistic Belgian multilingual clinical practice) -- the OPPOSITE
    direction from French/Dutch's own code_switch pools, which embed
    English fragments (that convention doesn't apply once English IS the
    base language).
  - DISTRACTORS["drug_brand"]: reused near-verbatim from French --
    Belgium registers medicines nationally, brand names are identical
    across every language community (confirmed for French, expected to
    hold for English too).
  - No PATIENT_NOUN_MARKED field: unlike French ("patient"/"patiente")
    and Dutch ("patient"/"patiente"), English "patient" has no separate
    masculine/feminine form at all, so there is nothing to mark --
    dropped entirely rather than kept as a dead field. PRONOUN_POSS
    ("his"/"her") is a simple per-case field, unlike French where it had
    to be dropped ("son"/"sa" agree with the POSSESSED noun's gender, not
    the possessor's sex) -- English "his"/"her" agree with the
    possessor's sex, exactly like Dutch "zijn"/"haar", so this is a real
    simplification versus French, not a gap to defend against.
  - HONORIFIC uses the standard English ABBREVIATED forms "Mr"/"Ms" (no
    periods, British style) -- unlike French "monsieur"/"madame" or
    Dutch "meneer"/"mevrouw", which are the NATURAL full-word forms in
    those languages, "Mr"/"Ms" IS the natural English form, not a
    shorthand deviation from something more standard.
  - `Faker("en_GB")` as the CLI default, since no en_BE locale exists --
    NOTE this is currently a vestigial parameter: `fake` is accepted by
    build_case() for interface parity with the French/Dutch signature but
    is not actually called anywhere in the body (true of the French file
    too -- verified by inspection, not a regression introduced here).

Usage
    python3 pii_table_en.py -n 2000 --out pii_table_en.csv --audit
    python3 pii_table_en.py -n 500 --label-scheme split --out split.csv
    python3 pii_table_en.py --demo            # show one filled template
"""

from __future__ import annotations

import argparse
import json
import random
import unicodedata
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta

try:
    from faker import Faker
except ImportError:
    raise SystemExit("pip install faker pandas")


# ===========================================================================
# Reference data: Belgium, nationally distributed
# ===========================================================================

# (zipcode, city, province, urbanicity, region, weight). Merged from the
# Dutch track's Flemish CITIES table (TamerBERT/TamerBERT/pii_table.py) and
# the French track's WALLOON_CITIES table (personal_finetune/french/
# pii_table_fr.py) -- both already contain real, verified Belgian
# municipalities; this table does not invent any new place names. Weights
# for the Walloon+Brussels entries are the REAL Statbel-derived figures
# already used by the French track (see that file for sourcing). Weights
# for the Flemish entries are ADDED here (the Dutch original sampled its
# CITIES list uniformly, with no population weighting at all) using
# approximate, order-of-magnitude-correct 2024 population figures for each
# named municipality -- flagged honestly as approximate, not a fresh
# Statbel pull, since the goal here is realistic national proportionality
# (Flanders is the most populous region, so it must not be under-weighted
# relative to Wallonia/Brussels the way a naive "just concatenate the two
# lists unweighted" merge would produce).
BELGIAN_CITIES = [
    # --- Flanders (weights: approximate 2024 population, order-of-
    #     magnitude sourced from public municipal population figures) ---
    ("2000", "Antwerp",              "Antwerp",         "urban", "Vlaanderen", 530000),
    ("9000", "Ghent",                "East Flanders",   "urban", "Vlaanderen", 264000),
    ("8000", "Bruges",               "West Flanders",   "urban", "Vlaanderen", 118000),
    ("3000", "Leuven",               "Flemish Brabant", "urban", "Vlaanderen", 104000),
    ("3500", "Hasselt",              "Limburg",         "urban", "Vlaanderen", 80000),
    ("9100", "Sint-Niklaas",         "East Flanders",   "town",  "Vlaanderen", 80000),
    ("9300", "Aalst",                "East Flanders",   "town",  "Vlaanderen", 87000),
    ("2800", "Mechelen",             "Antwerp",         "urban", "Vlaanderen", 86000),
    ("8500", "Kortrijk",             "West Flanders",   "urban", "Vlaanderen", 77000),
    ("3600", "Genk",                 "Limburg",         "town",  "Vlaanderen", 68000),
    ("8800", "Roeselare",            "West Flanders",   "town",  "Vlaanderen", 65000),
    ("8400", "Ostend",               "West Flanders",   "town",  "Vlaanderen", 71000),
    ("2300", "Turnhout",             "Antwerp",         "town",  "Vlaanderen", 47000),
    ("1800", "Vilvoorde",            "Flemish Brabant", "town",  "Vlaanderen", 46000),
    ("1930", "Zaventem",             "Flemish Brabant", "town",  "Vlaanderen", 32000),
    ("2400", "Mol",                  "Antwerp",         "rural", "Vlaanderen", 37000),
    ("2440", "Geel",                 "Antwerp",         "town",  "Vlaanderen", 41000),
    ("3700", "Tongeren",             "Limburg",         "rural", "Vlaanderen", 31000),

    # --- Flanders, round 2 additions (verified via web search, 2026-08-19:
    #     real municipalities + confirmed postal codes, added to broaden
    #     vocabulary coverage beyond the original 18-city Flemish list) ---
    ("9200", "Dendermonde",          "East Flanders",   "town",  "Vlaanderen", 46000),
    ("8600", "Diksmuide",            "West Flanders",   "rural", "Vlaanderen", 17000),
    ("8790", "Waregem",              "West Flanders",   "town",  "Vlaanderen", 38000),
    ("2200", "Herentals",            "Antwerp",         "town",  "Vlaanderen", 28000),
    ("1500", "Halle",                "Flemish Brabant", "town",  "Vlaanderen", 40000),
    ("3300", "Tienen",               "Flemish Brabant", "town",  "Vlaanderen", 35000),
    ("2500", "Lier",                 "Antwerp",         "town",  "Vlaanderen", 36000),
    ("9700", "Oudenaarde",           "East Flanders",   "town",  "Vlaanderen", 31000),
    ("9500", "Geraardsbergen",       "East Flanders",   "town",  "Vlaanderen", 34000),
    ("9800", "Deinze",               "East Flanders",   "town",  "Vlaanderen", 44000),
    ("9160", "Lokeren",              "East Flanders",   "town",  "Vlaanderen", 41000),
    ("3290", "Diest",                "Flemish Brabant", "town",  "Vlaanderen", 24000),
    ("3800", "Sint-Truiden",         "Limburg",         "town",  "Vlaanderen", 40000),

    # --- Wallonia (weights: REAL Statbel-derived figures, from the
    #     already-verified French-track table -- unchanged) ---
    ("4000", "Liège",                 "Liège", "urban", "Wallonie", 197013),
    ("6000", "Charleroi",             "Hainaut", "urban", "Wallonie", 204670),
    ("7000", "Mons",                  "Hainaut", "urban", "Wallonie", 93366),
    ("5000", "Namur",                 "Namur", "urban", "Wallonie", 110691),
    ("7500", "Tournai",               "Hainaut", "urban", "Wallonie", 69751),
    ("4100", "Seraing",               "Liège", "urban", "Wallonie", 63968),
    ("4800", "Verviers",              "Liège", "urban", "Wallonie", 56594),
    ("7100", "La Louvière",           "Hainaut", "town",  "Wallonie", 78895),
    ("6700", "Arlon",                 "Luxembourg", "town",  "Wallonie", 29733),
    ("1300", "Wavre",                        "Brabant Wallon", "town",  "Wallonie", 33277),
    ("1340", "Ottignies-Louvain-la-Neuve",   "Brabant Wallon", "urban", "Wallonie", 31190),
    ("1420", "Braine-l'Alleud",              "Brabant Wallon", "town",  "Wallonie", 40461),
    ("6900", "Marche-en-Famenne",     "Luxembourg", "town",  "Wallonie", 17454),
    ("6830", "Bouillon",              "Luxembourg", "rural", "Wallonie", 5426),

    # --- Wallonia, round 2 additions (verified via web search, 2026-08-19).
    #     Malmedy/Waterloo/Enghien/Binche/Rixensart mirrored into the French
    #     track's WALLOON_CITIES too (real Belgian facts, not English-
    #     specific). Eupen is EN-only, deliberately NOT mirrored into
    #     French: it's the capital of Belgium's German-speaking Community
    #     (German is the official/legal-administrative language there, not
    #     French) -- the same reasoning this file already applies by never
    #     borrowing Flemish cities into the French track. It stays here
    #     because English's "nationally distributed" design explicitly
    #     doesn't tie document language to regional administrative
    #     language the way the French/Dutch tracks do. ---
    ("4700", "Eupen",                 "Liège", "town",  "Wallonie", 20000),
    ("4960", "Malmedy",               "Liège", "rural", "Wallonie", 12500),
    ("1410", "Waterloo",              "Brabant Wallon", "town", "Wallonie", 30000),
    ("7850", "Enghien",               "Hainaut", "rural", "Wallonie", 13500),
    ("7130", "Binche",                "Hainaut", "town", "Wallonie", 33000),
    ("1330", "Rixensart",             "Brabant Wallon", "town", "Wallonie", 22000),

    # --- Brussels-Capital (bilingual EN documents are especially plausible
    #     here -- EU institutions, international schools, NATO -- so a
    #     larger relative share than the Dutch/French tracks' deliberately
    #     down-scaled Brussels weight is realistic for THIS population) ---
    ("1000", "Brussels",              "Brussels-Capital", "urban", "Bruxelles-Capitale", 200000),
    ("1050", "Ixelles",               "Brussels-Capital", "urban", "Bruxelles-Capitale", 90000),
    ("1040", "Etterbeek",             "Brussels-Capital", "urban", "Bruxelles-Capitale", 55000),
    ("1150", "Woluwe-Saint-Pierre",   "Brussels-Capital", "urban", "Bruxelles-Capitale", 42000),
    ("1180", "Uccle",                 "Brussels-Capital", "urban", "Bruxelles-Capitale", 84000),
    ("1200", "Woluwe-Saint-Lambert",  "Brussels-Capital", "urban", "Bruxelles-Capitale", 57000),
]

# Real Belgian hospital naming, merged from both already-verified tracks:
# Dutch AZ/UZ network (TamerBERT/TamerBERT/pii_table.py) + French CHU/CHR/
# Clinique network (personal_finetune/french/pii_table_fr.py). Nationally
# distributed English-language documents plausibly come from either.
HOSPITAL_PREFIX = ["AZ", "UZ", "CHU", "CHR", "Clinique", "Hôpital", "Ziekenhuis"]
HOSPITAL_STEM = [
    # Flemish stems (Dutch track)
    "Sint-Lucas", "Sint-Vincentius", "Sint-Jozef", "Sint-Rembert", "Sint-Blasius",
    "Onze-Lieve-Vrouw", "Heilig Hart", "Maria Middelares", "Groeninge",
    "Vesalius", "Damiaan", "Nikolaas", "Rivierenland",
    # Walloon/Brussels stems (French track)
    "Saint-Pierre", "Saint-Luc", "Saint-Joseph", "Sainte-Élisabeth",
    "Notre-Dame", "Sainte-Thérèse", "Reine Fabiola", "Reine Astrid",
    "Citadelle", "Ambroise Paré",
]
HOSPITAL_STANDALONE = [
    # Flemish (Dutch track)
    "ZNA Middelheim", "AZ Klina", "AZ Delta", "AZ Turnhout",
    "Jessa Ziekenhuis", "Imeldaziekenhuis", "AZ Alma",
    # Flemish, round 2 additions (verified via web search, 2026-08-19) --
    # the original 7-name Flemish list was badly outweighed by the 28
    # Walloon/Brussels names below despite English being explicitly
    # nationally distributed, so this specifically closes that gap:
    # UZ Gent (en.wikipedia.org/wiki/Ghent_University_Hospital), UZ Leuven
    # (Belgium's largest university hospital, KU Leuven-affiliated), UZA
    # (Antwerp University Hospital, Edegem), AZ Sint-Jan Brugge-Oostende AV,
    # AZ Jan Palfijn Gent, ZNA Sint-Erasmus (part of the ZNA Antwerp group,
    # alongside ZNA Middelheim already above), Ziekenhuis Oost-Limburg (ZOL,
    # Genk -- Limburg's largest hospital), AZ Sint-Maarten (Mechelen).
    "UZ Gent", "UZ Leuven", "UZA", "AZ Sint-Jan Brugge-Oostende AV",
    "AZ Jan Palfijn Gent", "ZNA Sint-Erasmus", "Ziekenhuis Oost-Limburg",
    "AZ Sint-Maarten",
    # Walloon/Brussels (French track) -- full list reused, AVIQ-registry-
    # sourced, see personal_finetune/french/pii_table_fr.py for the
    # per-institution provenance notes
    "CHU de Liège - site Sart Tilman", "CHU de Liège - site Notre-Dame des Bruyères",
    "CHR de la Citadelle", "CHC MontLégia", "CHR Huy", "CHR Verviers",
    "CHU UCL Namur - site Sainte-Élisabeth", "CHU UCL Namur - site Godinne",
    "Grand Hôpital de Charleroi - site Notre-Dame",
    "Grand Hôpital de Charleroi - site Saint-Joseph",
    "CHU Charleroi - Hôpital civil Marie Curie", "CHU Ambroise Paré",
    "Centre Hospitalier Régional Mons-Hainaut", "CHwapi - site Union",
    "CHU Tivoli", "Hôpital de Jolimont",
    "Vivalia - Hôpital d'Arlon", "Vivalia - Hôpital de Marche",
    "Clinique Saint-Pierre Ottignies", "Cliniques universitaires de Mont-Godinne",
    "CHU Saint-Pierre", "CHU Brugmann", "HUDERF", "Institut Jules Bordet",
    "Cliniques universitaires Saint-Luc", "Hôpital Erasme",
    "CHIREC - Hôpital Delta", "Cliniques de l'Europe",
]

# Street naming is REGION-AWARE, not a single national convention -- Dutch
# compound-word style (Kerkstraat) for Flemish cities, French
# "[type] + de/du/des" style (Rue de la Gare) for Walloon/Brussels cities.
# Reusing both tracks' already-verified vocabulary unchanged; there is no
# "English street name" convention to invent (locked-in decision).
STREET_STEM = [
    "Kerk", "Dorp", "Molen", "Nieuw", "Oude", "Hoge", "Lange", "Korte", "Groene",
    "Stations", "School", "Veld", "Berg", "Beek", "Linde", "Eiken", "Wilgen",
    "Bloem", "Zonne", "Vijver", "Kasteel", "Abdij", "Markt", "Vissers", "Smid",
]
STREET_SUFFIX = [
    "straat", "laan", "steenweg", "dreef", "weg", "plein", "kaai", "baan",
    "pad", "lei", "vest", "wal", "berg", "hof", "dries", "park", "ring",
]
STREET_TYPE = [
    "Rue", "Chemin", "Avenue", "Place", "Clos", "Route", "Allée",
    "Chaussée", "Ruelle", "Impasse", "Drève", "Boulevard", "Square", "Quai",
]
STREET_THEME = [
    "de la Gare", "du Moulin", "des Champs", "de l'Église", "du Château",
    "de la Fontaine", "du Pont", "de la Chapelle", "des Écoles",
    "de la Station", "de la Croix", "des Tilleuls", "du Chêne",
    "des Marronniers", "du Bois", "de la Prairie", "des Prés",
    "Saint-Roch", "Sainte-Anne", "Saint-Nicolas", "Saint-Hubert",
    "de la Vallée", "de l'Étang", "de la Meuse", "du Marché",
    "de Namur", "de Charleroi", "de Bruxelles", "de Liège", "Albert Ier",
]


def make_street(rng: random.Random, region: str) -> str:
    """Region-aware street name -- Dutch compound style for Flanders,
    French "type + theme" style for Wallonia/Brussels."""
    if region == "Vlaanderen":
        return f"{rng.choice(STREET_STEM)}{rng.choice(STREET_SUFFIX)}"
    return f"{rng.choice(STREET_TYPE)} {rng.choice(STREET_THEME)}"


# Name pools stratified by origin. Two pools ("flemish", "walloon") are
# REUSED VERBATIM from the already-verified Dutch/French tracks -- a native
# Belgian patient can genuinely receive an English-language letter too
# (international hospital departments, English-speaking specialists,
# bilingual Brussels institutions), and the model needs real exposure to
# native Belgian names regardless of what population the English track is
# primarily modelling, or it will never learn to detect them correctly in
# an English-language document. The remaining five pools are rebuilt
# around the REAL expat/international population actually treated in
# English in Belgium (there is no native English-speaking linguistic
# region in Belgium the way there is for French/Dutch). See module
# docstring for why the expat-pool weights are a reasoned estimate, not
# Statbel-sourced like French/Dutch's own native-population weights.
#   - flemish / walloon: unchanged from Dutch/French, native Belgian
#     coverage (see those files for full provenance notes).
#   - uk_ireland: the single largest historically-rooted English-speaking
#     expat community in Belgium (EU institutions have drawn UK/Irish
#     staff since long before Brexit; large surviving Irish/British
#     community particularly in Brussels).
#   - us: US nationals via NATO, EU-adjacent diplomatic missions, and
#     multinational corporate presence concentrated in Brussels.
#   - other_eu_staff: the LARGEST single expat category by design -- EU
#     institution staff from non-English-mother-tongue member states who
#     conduct business in English as a lingua franca (the actual dominant
#     real-world case for "English-language Belgian medical document",
#     arguably more common than native-English speakers).
#   - anglophone_africa: Nigeria specifically, a well-documented Anglophone
#     African community in Belgium (Brussels in particular).
#   - anglophone_asia: India specifically, a well-documented Anglophone
#     South Asian professional community (IT, EU-institution-adjacent
#     contracting) in Belgium.
# Round 2 additions (2026-08-19, +5 male/+5 female/+5 surnames per origin)
# widen each pool's vocabulary; common-knowledge naming data for each
# community, not obscure facts requiring citation, so added directly
# without a web-verification pass (unlike the CITIES/HOSPITAL_STANDALONE
# additions above, which are specific real-world institutions/places).
NAMES = {
    "flemish": {
        "w": 0.14,
        "m": ["Jan", "Marc", "Luc", "Dirk", "Wim", "Bart", "Kris", "Tom", "Stijn",
              "Jonas", "Wouter", "Filip", "Geert", "Koen", "Pieter", "Lode", "Rik",
              "Bram", "Niels", "Sander", "Wesley", "Tim"],
        "f": ["An", "Els", "Katrien", "Griet", "Lieve", "Ann", "Sofie", "Leen",
              "Marleen", "Hilde", "Veerle", "Inge", "Nele", "Tine", "Femke", "Lore",
              "Fien", "Marte", "Britt", "Sien", "Jitske"],
        "s": ["Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Willems",
              "Claes", "Goossens", "Wouters", "De Smet", "Dubois", "Lambert",
              "Van den Berghe", "Vermeulen", "De Clercq", "Van Damme",
              "Verhoeven", "De Backer", "Coppens", "Van Acker", "Declercq",
              "De Vos", "Van Loo", "Verstraete", "Pauwels", "Vandenberghe"],
    },
    "walloon": {
        "w": 0.11,
        "m": ["Jean", "Pierre", "Marc", "Michel", "Nicolas", "Vincent",
              "Julien", "Olivier", "Laurent", "Benoît", "Thomas", "Xavier",
              "Fabrice", "Yves", "Christophe", "Guillaume", "Damien", "Denis",
              "Alain", "Bernard", "Philippe", "Raymond", "Stéphane"],
        "f": ["Marie", "Sophie", "Catherine", "Anne", "Isabelle", "Nathalie",
              "Julie", "Caroline", "Valérie", "Céline", "Aurélie", "Laëtitia",
              "Charlotte", "Camille", "Delphine", "Manon", "Émilie", "Sarah",
              "Chantal", "Christine", "Véronique", "Martine", "Brigitte"],
        "s": ["Dubois", "Lambert", "Simon", "Léonard", "Georges", "Renard",
              "Collard", "Delcourt", "Herman", "Fontaine", "Gérard", "Michel",
              "Marchal", "Toussaint", "Lejeune", "Dupont", "Thomas", "Nicolas",
              "Bertrand", "Servais", "Halleux", "Delvaux",
              "Lefebvre", "Renaud", "Poncelet", "Colin", "Massart"],
    },
    "uk_ireland": {
        "w": 0.19,
        "m": ["James", "Oliver", "George", "Thomas", "William", "Harry",
              "Jack", "Charlie", "Daniel", "Ryan", "Sean", "Liam",
              "Connor", "Aidan", "Declan",
              "Ethan", "Callum", "Finn", "Cormac", "Rory"],
        "f": ["Emily", "Charlotte", "Olivia", "Amelia", "Sophie", "Grace",
              "Emma", "Chloe", "Aoife", "Niamh", "Siobhan", "Ciara",
              "Saoirse",
              "Isla", "Freya", "Molly", "Erin", "Roisin"],
        "s": ["Smith", "Jones", "Taylor", "Brown", "Wilson", "Evans",
              "Murphy", "Kelly", "O'Brien", "Byrne", "Ryan", "Walsh",
              "McCarthy", "Doyle",
              "Fitzgerald", "Kavanagh", "Sullivan", "Campbell", "Reid"],
    },
    "us": {
        "w": 0.10,
        "m": ["Michael", "Christopher", "Matthew", "Joshua", "Andrew",
              "Tyler", "Brandon", "Justin", "Kevin", "Brian",
              "Jordan", "Austin", "Cody", "Derek", "Marcus"],
        "f": ["Jessica", "Ashley", "Amanda", "Jennifer", "Samantha",
              "Lauren", "Megan", "Brittany", "Rachel", "Stephanie",
              "Kayla", "Nicole", "Amber", "Courtney", "Heather"],
        "s": ["Johnson", "Williams", "Anderson", "Thompson", "Martinez",
              "Robinson", "Clark", "Rodriguez", "Lewis", "Walker",
              "Harris", "Young", "King", "Wright", "Scott"],
    },
    "other_eu_staff": {
        "w": 0.22,
        "m": ["Lukas", "Matteo", "Pierre", "Hans", "Jan", "Miguel",
              "Andreas", "Stefan", "Jean", "Marco",
              "Antoine", "Wolfgang", "Erik", "Luca", "Tomas"],
        "f": ["Sofia", "Anna", "Marie", "Elena", "Ingrid", "Isabel",
              "Greta", "Katarina", "Lucia", "Nadine",
              "Claudia", "Petra", "Simone", "Karin", "Beatriz"],
        "s": ["Müller", "Rossi", "Dubois", "Van der Berg", "García",
              "Kowalski", "Nilsson", "Novak", "Bakker", "Moreau",
              "Schmidt", "Laurent", "Andersson", "Hoffmann", "Petit"],
    },
    "anglophone_africa": {
        "w": 0.13,
        "m": ["Chukwuemeka", "Oluwaseun", "Emeka", "Ikenna", "Tunde",
              "Chinedu", "Babajide", "Uche", "Kelechi", "Femi",
              "Chibuzor", "Obinna", "Ayodele", "Segun", "Chukwudi"],
        "f": ["Ngozi", "Chidinma", "Adaeze", "Funmilayo", "Amara",
              "Chiamaka", "Yetunde", "Oluwakemi", "Ijeoma", "Blessing",
              "Folake", "Nkechi", "Onyinye", "Temitope", "Adaobi"],
        "s": ["Okafor", "Adeyemi", "Okonkwo", "Eze", "Balogun", "Nwosu",
              "Adebayo", "Chukwu", "Okoro", "Afolabi",
              "Nnamdi", "Uzoma", "Chikezie", "Okeke", "Anyanwu"],
    },
    "anglophone_asia": {
        "w": 0.11,
        "m": ["Rohan", "Arjun", "Aditya", "Vikram", "Rahul", "Karan",
              "Amit", "Nikhil", "Sanjay", "Rajesh",
              "Siddharth", "Varun", "Ravi", "Manoj", "Deepak"],
        "f": ["Priya", "Ananya", "Neha", "Divya", "Pooja", "Kavya",
              "Meera", "Anjali", "Shreya", "Isha",
              "Radhika", "Swati", "Nandini", "Preeti", "Sneha"],
        "s": ["Sharma", "Patel", "Kumar", "Singh", "Gupta", "Reddy",
              "Iyer", "Nair", "Menon", "Rao",
              "Chopra", "Bose", "Verma", "Joshi", "Pillai"],
    },
}

# British/international spelling and terminology (locked-in decision).
SPECIALTIES = [
    "Gastroenterology", "Physical Medicine and Rehabilitation", "Ophthalmology",
    "Respiratory Medicine", "Cardiology", "Neurology", "Dermatology", "Endocrinology",
    "Nephrology", "Orthopaedics", "Urology", "Gynaecology", "Rheumatology",
    "Oncology", "ENT", "Geriatrics", "Vascular Surgery", "General Surgery",
]

# (diagnosis, specialty, sex_restriction) -- sex_restriction None = either.
# Translated from the French track's medically-verified DIAGNOSES list
# (itself verified against Belgian clinical usage, not machine translation)
# into British/international English -- e.g. "anaemia" not "anemia",
# "oesophagitis" not "esophagitis", "coeliac" not "celiac".
DIAGNOSES = [
    ("anal fissure",                                  "Gastroenterology", None),
    ("mild chronic non-specific colitis",             "Gastroenterology", None),
    ("anastomotic ulcer",                              "Gastroenterology", None),
    ("iron-deficiency anaemia",                        "Gastroenterology", None),
    ("status post gastric bypass (RYGB)",              "Gastroenterology", None),
    ("reflux oesophagitis, grade B",                   "Gastroenterology", None),
    ("sigmoid diverticulosis",                         "Gastroenterology", None),
    ("coeliac disease",                                "Gastroenterology", None),
    ("left epididymitis",                              "Urology",           "M"),
    ("bilateral supraspinatus tendinosis",             "Physical Medicine and Rehabilitation", None),
    ("subacromial bursitis",                           "Physical Medicine and Rehabilitation", None),
    ("pelvic floor hypertonicity",                     "Physical Medicine and Rehabilitation", None),
    ("right lateral epicondylitis",                    "Physical Medicine and Rehabilitation", None),
    ("lumbar facet syndrome",                          "Physical Medicine and Rehabilitation", None),
    ("no diabetic retinopathy",                        "Ophthalmology",       None),
    ("bilateral incipient cataract",                   "Ophthalmology",       None),
    ("open-angle glaucoma",                             "Ophthalmology",       None),
    ("dry age-related macular degeneration",           "Ophthalmology",       None),
    ("chronic obstructive pulmonary disease, GOLD stage II", "Respiratory Medicine", None),
    ("well-controlled asthma",                         "Respiratory Medicine", None),
    ("obstructive sleep apnoea syndrome",              "Respiratory Medicine", None),
    ("Von Willebrand disease",                         "General Surgery",     None),
    ("epilepsy in remission",                          "Neurology",          None),
    ("migraine with aura",                             "Neurology",          None),
    ("peripheral polyneuropathy",                      "Neurology",          None),
    ("type 2 diabetes mellitus",                       "Endocrinology",      None),
    ("hypothyroidism",                                 "Endocrinology",      None),
    ("osteoporosis",                                   "Rheumatology",       None),
    ("rheumatoid arthritis",                           "Rheumatology",       None),
    ("atrial fibrillation",                            "Cardiology",         None),
    ("arterial hypertension",                          "Cardiology",         None),
    ("chronic kidney disease stage 3",                 "Nephrology",         None),
    ("bilateral knee osteoarthritis",                  "Orthopaedics",       None),
    ("carpal tunnel syndrome",                         "Orthopaedics",       None),
    ("benign prostatic hyperplasia",                   "Urology",            "M"),
    ("endometriosis",                                  "Gynaecology",        "F"),
    ("fibroid uterus",                                 "Gynaecology",        "F"),
    ("atopic eczema",                                  "Dermatology",        None),
    ("psoriasis vulgaris",                             "Dermatology",        None),
    ("chronic rhinosinusitis",                         "ENT",                None),
]

AGE_BANDS = [(0, 17, 0.06), (18, 34, 0.16), (35, 49, 0.19),
             (50, 64, 0.24), (65, 79, 0.24), (80, 95, 0.11)]

# Label-phrasing pools for the literal text rendered immediately before
# {INSZ}/{RIZIV} in every template. Sampled per-case in build_case() so
# label-context variety is baked into the corpus from generation -- root fix
# for the INSZ positional-rigidity issue validate_diversity_en.py flagged
# (100% of the 50 hand-translated templates hardcoded the identical literal
# "National Registration No." with zero variation). Deliberately shaped
# variants, not near-synonyms sharing a tail (a short abbreviation like
# "NRN" and a differently-positioned phrase like "N° NIHDI" collapse to
# DIFFERENT last-12-characters shapes; near-synonyms sharing "...No." would
# not). Formerly lived in augment_en.py as an augmentation-time patch
# (_REG_LABELS/_NIHDI_LABELS, xf_id_label_variant) -- removed from there now
# that this is fixed at the source, since augmentation can only ADD
# transformed copies on top of unmodified originals, capping how far a
# downstream-only fix can go.
LABEL_POOL_INSZ = ["National Registration No.", "NRN", "Reg. No.",
                   "National ID", "ID No."]
LABEL_POOL_RIZIV = ["NIHDI No.", "N° NIHDI", "Provider ID",
                    "INAMI/NIHDI No.", "Physician ID"]


# ===========================================================================
# HARD NEGATIVES
# These are strings that LOOK like PII and must be tagged O. Same rationale
# as Dutch/French: without them the model never learns to reject a
# municipality name embedded in an ordinary word.
# ===========================================================================

DISTRACTORS = {
    # English eponym convention uses the possessive 's, unlike French's
    # "maladie de X" -- translated accordingly, not machine-transliterated.
    "eponym_disease": [
        "Von Willebrand disease", "Crohn's disease", "Parkinson's disease",
        "Sjögren's syndrome", "Raynaud's syndrome", "Graves' disease",
        "Bechterew's disease", "Guillain-Barré syndrome",
        "Lasègue's sign", "Valsalva manoeuvre", "Hashimoto's disease",
        "Cushing's syndrome", "Dupuytren's disease",
    ],
    "eponym_test": [
        "Snellen test", "Humphrey test", "Jaeger test",
        "Goldmann applanation", "Schirmer test", "Tinel's sign",
        "Phalen's manoeuvre", "Romberg negative", "Glasgow Coma Scale 15",
        "Barthel index 90", "Bristol stool scale type 4",
    ],
    # Standard English anatomical abbreviation convention (m.=muscle,
    # n.=nerve, a.=artery, lig.=ligament, v.=vein) -- direct equivalent of
    # French's "French adjective + Latin genus abbreviation" convention,
    # just following English's own real convention rather than copying
    # French's grammatical shape.
    "anatomy_latin": [
        "long head of biceps (LHB)", "supraspinatus m.", "infraspinatus m.",
        "median n.", "radial a.", "medial collateral lig.",
        "great saphenous v.",
    ],
    # Belgium registers medicines nationally -- brand names are identical
    # across language communities (confirmed for French via CBIP/
    # e-compendium.be; expected to hold for English-language documents in
    # Belgium too, since the packaging itself doesn't change by the
    # patient's document language) -- reused near-verbatim from French.
    "drug_brand": [
        "Asaflow 80 mg", "Atorstatine 20 mg", "D-cure 25,000 IU",
        "GlucaGen hypokit", "Lyumjev kwikpen", "Toujeo solostar",
        "Lambipol 100 mg", "L-thyroxine 50 mcg", "Metformine viatris 500 mg",
        "Nexiam 20 mg", "Ozempic 1 mg", "Progor retard 180 mg",
        "Sipralexa 20 mg", "Depakine chrono 500 mg", "Pantomed 40 mg",
        "Injectafer 1000 mg", "Ventolin aerosol", "Diltiazem gel 2%",
        "Cose protect", "Trianal suppo", "Ibuprofen 400 mg", "Paracetamol 1 g",
    ],
    # Fresh English-specific research (NOT translated from French/Dutch's
    # own homograph lists, which are homographs against French/Dutch words
    # respectively -- an entirely different collision class). Real Belgian
    # place names that also happen to be ordinary English words.
    # DELIBERATELY a small, honestly-verified starter set (same principle
    # French applied with its own 4-entry list): Spa (Liège province --
    # the actual etymological origin of the English word "spa"), Peer
    # (Limburg municipality / English "a peer"), Ways (a hamlet of
    # Genappe, Brabant Wallon / English "ways"), Marche (Marche-en-Famenne
    # / English "march" -- a genuinely different collision from French's
    # own reading of the same town as "marche" = gait/walking).
    "municipality_homograph": [
        "referred for a spa treatment course",       # Spa
        "reviewed by a peer prior to discharge",     # Peer
        "explored several treatment ways",           # Ways
        "the patient will march to full recovery",   # Marche
    ],
    # Continental European 24h-clock convention kept (realistic for a
    # "Belgian doctor writing in English" register -- locked-in decision),
    # with IU replacing French UI and English shorthand elsewhere.
    "numeric_lookalike": [
        "1x/day", "2x/day", "1x/week", "3x/week", "1-2/day", "08:00", "12:00",
        "18:00", "22:00", "BP: 146/68", "HR: 68", "SpO2: 94%", "2cc", "3x",
        "25,000 IU", "100u/ml 3ml", "300 IU/ml 1.5ml", "0.5mg", "4.95*",
        "-0.25 ^ -0.25 axis 165 degrees", "FEV1/FVC 73.17", "BMI 20.808",
        "T 37.2", "pH 7.38", "D+7", "D15",
    ],
    # Real English clinical abbreviations/shorthand -- fresh research, not
    # a translation of French's ATCD/RAS/TTT set (no 1:1 mapping exists;
    # English clinicians use their own real shorthand conventions).
    "abbreviation": [
        "PMHx", "NAD", "Rx", "Hx", "Dx", "Tx", "FHx", "WNL", "NKDA", "c/o", "o/e",
    ],
    # International proper nouns (not French/Dutch-specific to begin
    # with), so ported unchanged -- same reasoning French used to port
    # these unchanged from Dutch.
    "_ambiguous_surnames": [
        "Snellen", "Jaeger", "Graves", "Romberg", "Phalen", "Goldmann",
        "Schirmer", "Tinel", "Bristol", "Barthel",
    ],
    # For ENGLISH documents, code-switching runs the OPPOSITE direction
    # from French/Dutch's own code_switch pools (which embed English
    # fragments into French/Dutch prose -- that convention doesn't apply
    # once English IS the base language). Realistic Belgian multilingual
    # clinical practice: a Belgian doctor writing in English plausibly
    # drops in a French or Dutch clinical phrase.
    "code_switch": [
        "sans particularité", "à revoir en consultation", "état général conservé",
        "pas de récidive", "geen bijzonderheden", "goede algemene toestand",
        "ter observatie", "in orde",
    ],
    # CNK ("Code National") -- the 7-digit Belgian drug-reimbursement
    # identifier, national and not language-bound, reused verbatim from
    # French.
    "cnk_code": [
        "0730-011", "1425-478", "2093-655", "3186-042", "4271-390",
        "5044-827", "6318-155", "7402-963", "8155-704", "9027-236",
    ],
    # BELAC accreditation number -- Belgian, facility-level, not language-
    # bound, reused verbatim from French.
    "belac_number": ["BELAC 128-MED", "BELAC 203-MED", "BELAC 077-MED", "BELAC 311-MED"],
}


# ---------------------------------------------------------------------------
# Character-level noise: simulates PRE-normalization text. Unchanged from
# Dutch/French -- pure Unicode-level, language-agnostic.
# ---------------------------------------------------------------------------

NOISE_OPS = {
    "nbsp":        lambda s, r: s.replace(" ", " ", 1) if " " in s else s,
    "narrow_nbsp": lambda s, r: s.replace(" ", " ", 1) if " " in s else s,
    "soft_hyphen": lambda s, r: (s[:len(s)//2] + "­" + s[len(s)//2:]
                                 if len(s) > 8 else s),
    "zwsp":        lambda s, r: (s[:len(s)//2] + "​" + s[len(s)//2:]
                                 if len(s) > 8 else s),
    "curly_quote": lambda s, r: s.replace("'", "’"),
    "en_dash":     lambda s, r: s.replace("-", "–", 1) if "-" in s else s,
    "nb_hyphen":   lambda s, r: s.replace("-", "‑", 1) if "-" in s else s,
    "nfd":         lambda s, r: unicodedata.normalize("NFD", s),
}


def inject_noise(value: str, rng: random.Random, rate: float):
    """Returns (possibly-corrupted value, op name or None)."""
    if rate <= 0 or rng.random() > rate:
        return value, None
    op = rng.choice(list(NOISE_OPS))
    try:
        return NOISE_OPS[op](value, rng), op
    except Exception:
        return value, None


# ===========================================================================
# Belgian identifier construction (real checksums) -- UNCHANGED from
# Dutch/French. These are national Belgian formats, not language-bound.
# ===========================================================================

def make_insz(birth: date, sex: str, rng: random.Random) -> str:
    """11 digits: YYMMDD + SSS (odd=M, even=F) + CC (mod-97 check)."""
    yy, mm, dd = birth.year % 100, birth.month, birth.day
    while True:
        seq = rng.randrange(1, 998)
        if (seq % 2 == 1) == (sex == "M"):
            break
    base = f"{yy:02d}{mm:02d}{dd:02d}{seq:03d}"
    mod_src = base if birth.year < 2000 else "2" + base
    check = 97 - (int(mod_src) % 97)
    return base + f"{check:02d}"


def make_riziv(rng: random.Random) -> str:
    """11 digits: 6 base + 2 check (mod-97) + 3 qualification code."""
    base = rng.randrange(100000, 999999)
    check = 97 - (base % 97)
    qual = rng.choice(["003", "004", "006", "007", "008", "018", "030", "480"])
    return f"{base:06d}{check:02d}{qual}"


def make_iban_be(rng: random.Random) -> str:
    """BE + 2 check + 12 digits, validated mod-97 == 1."""
    body = f"{rng.randrange(0, 10**12):012d}"
    rearr = body + "1114" + "00"
    check = 98 - (int(rearr) % 97)
    return f"BE{check:02d}{body}"


def luhn_card(rng: random.Random) -> str:
    """Synthetic 16-digit card passing Luhn. Test range only."""
    d = [4] + [rng.randrange(10) for _ in range(14)]
    s = 0
    for i, x in enumerate(reversed(d)):
        x = x * 2 if i % 2 == 0 else x
        s += x - 9 if x > 9 else x
    d.append((10 - s % 10) % 10)
    return "".join(map(str, d))


# ===========================================================================
# Surface-format variants (sampled, and recorded) -- Belgian-structural
# functions are unchanged; the two that embed language content (fmt_address's
# floor words, fmt_url's path words) are forked.
# ===========================================================================

def fmt_insz(d: str, rng) -> tuple[str, str]:
    v = rng.choices(
        ["plain", "dotted", "spaced", "mixed"], weights=[0.55, 0.25, 0.13, 0.07])[0]
    if v == "dotted":  return f"{d[0:2]}.{d[2:4]}.{d[4:6]}-{d[6:9]}.{d[9:]}", v
    if v == "plain":   return d, v
    if v == "spaced":  return f"{d[0:2]} {d[2:4]} {d[4:6]} {d[6:9]} {d[9:]}", v
    return f"{d[0:2]}.{d[2:4]}.{d[4:6]} {d[6:9]} {d[9:]}", v


def fmt_riziv(d: str, rng) -> tuple[str, str]:
    v = rng.choices(["dashed", "plain", "spaced"], weights=[0.6, 0.2, 0.2])[0]
    if v == "dashed": return f"{d[0]}-{d[1:6]}-{d[6:8]}-{d[8:]}", v
    if v == "plain":  return d, v
    return f"{d[0]} {d[1:6]} {d[6:8]} {d[8:]}", v


def fmt_iban(s: str, rng) -> tuple[str, str]:
    v = rng.choices(["grouped", "plain"], weights=[0.7, 0.3])[0]
    if v == "grouped":
        return " ".join(s[i:i+4] for i in range(0, len(s), 4)), v
    return s, v


def make_phone(rng: random.Random, kind: str | None = None) -> tuple[str, str, str]:
    """Returns (surface, variant, kind). Belgian area-code table -- national,
    language-independent, unchanged from Dutch/French."""
    kind = kind or rng.choices(["landline", "mobile", "service"],
                               weights=[0.42, 0.48, 0.10])[0]
    if kind == "mobile":
        area = rng.choice(["0470", "0471", "0472", "0473", "0474", "0475", "0476",
                           "0477", "0478", "0479", "0483", "0484", "0485", "0486",
                           "0487", "0488", "0489", "0490", "0491", "0492", "0493",
                           "0495", "0496", "0497", "0498", "0499", "0456"])
        rest = [f"{rng.randrange(100):02d}" for _ in range(3)]
    elif kind == "service":
        area = rng.choice(["0800", "0900", "070", "078"])
        n = 5 if area in ("0800", "0900") else 6
        digits = "".join(str(rng.randrange(10)) for _ in range(n))
        if n % 2:
            rest = [digits[:1]] + [digits[i:i + 2] for i in range(1, n, 2)]
        else:
            rest = [digits[i:i + 2] for i in range(0, n, 2)]
    else:
        two = rng.random() < 0.4
        area = rng.choice(["02", "03", "04", "09"]) if two else rng.choice(
            ["010", "011", "012", "013", "014", "015", "016", "019", "050", "051",
             "052", "053", "054", "055", "056", "057", "058", "059", "089"])
        n = 7 if two else 6
        digits = "".join(str(rng.randrange(10)) for _ in range(n))
        rest = [digits[i:i+2] for i in range(0, len(digits) - (n % 2), 2)]
        if n % 2:
            rest = [digits[:3]] + [digits[i:i+2] for i in range(3, n, 2)]

    v = rng.choices(
        ["spaced", "slash_dot", "plain", "intl", "intl_paren", "dashed"],
        weights=[0.34, 0.22, 0.10, 0.16, 0.08, 0.10])[0]
    body = rest
    if v == "spaced":     s = f"{area} " + " ".join(body)
    elif v == "slash_dot": s = f"{area}/" + ".".join(body)
    elif v == "plain":     s = area + "".join(body)
    elif v == "intl":      s = f"+32 {area[1:]} " + " ".join(body)
    elif v == "intl_paren":s = f"+32 (0){area[1:]}/" + ".".join(body)
    else:                  s = f"{area}-" + " ".join(body)
    return s, v, kind


def fmt_date(d: date, rng: random.Random, allow_partial=True) -> tuple[str, str]:
    MONTHS = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    yy = d.year % 100
    opts = ["dd/mm/yyyy", "dd-mm-yyyy", "dd.mm.yyyy", "d/m/yyyy",
            "yyyy-mm-dd", "text_en", "text_abbr",
            "dd/mm/yy", "dd-mm-yy", "dd.mm.yy"]
    wts = [0.28, 0.25, 0.06, 0.07, 0.08, 0.09, 0.09, 0.04, 0.02, 0.02]
    if allow_partial:
        opts += ["dd/mm", "dd-mm", "dd.mm", "d/m",
                 "mm/yyyy", "m/yyyy", "mm.yyyy", "yyyy",
                 "yyyy-mm", "yyyy/mm", "yyyy.mm",
                 "yyyymmdd", "yymmdd"]
        wts += [0.03, 0.02, 0.01, 0.02,
                0.02, 0.015, 0.01, 0.015,
                0.01, 0.005, 0.005,
                0.015, 0.01]
    v = rng.choices(opts, weights=wts[:len(opts)])[0]
    m = {
        "dd/mm/yyyy": f"{d.day:02d}/{d.month:02d}/{d.year}",
        "dd-mm-yyyy": f"{d.day:02d}-{d.month:02d}-{d.year}",
        "dd.mm.yyyy": f"{d.day:02d}.{d.month:02d}.{d.year}",
        "d/m/yyyy":   f"{d.day}/{d.month}/{d.year}",
        "yyyy-mm-dd": d.isoformat(),
        "text_en":    f"{d.day} {MONTHS[d.month-1]} {d.year}",
        "text_abbr":  f"{d.day} {MONTHS[d.month-1][:3]} {d.year}",
        "dd/mm/yy":   f"{d.day:02d}/{d.month:02d}/{yy:02d}",
        "dd-mm-yy":   f"{d.day:02d}-{d.month:02d}-{yy:02d}",
        "dd.mm.yy":   f"{d.day:02d}.{d.month:02d}.{yy:02d}",
        "dd/mm":      f"{d.day:02d}/{d.month:02d}",
        "dd-mm":      f"{d.day:02d}-{d.month:02d}",
        "dd.mm":      f"{d.day:02d}.{d.month:02d}",
        "d/m":        f"{d.day}/{d.month}",
        "mm/yyyy":    f"{d.month:02d}/{d.year}",
        "m/yyyy":     f"{d.month}/{d.year}",
        "mm.yyyy":    f"{d.month:02d}.{d.year}",
        "yyyy":       f"{d.year}",
        "yyyy-mm":    f"{d.year}-{d.month:02d}",
        "yyyy/mm":    f"{d.year}/{d.month:02d}",
        "yyyy.mm":    f"{d.year}.{d.month:02d}",
        "yyyymmdd":   f"{d.year}{d.month:02d}{d.day:02d}",
        "yymmdd":     f"{yy:02d}{d.month:02d}{d.day:02d}",
    }
    return m[v], v


def fmt_dob_marker(d: date, rng: random.Random) -> tuple[str, str]:
    """The Belgian birth marker. Occasionally uses the English text-month
    form instead of a numeric date. Ring symbols kept unchanged from
    Dutch/French -- typographic/OCR-related, not language content."""
    ring = rng.choices(["°", "º"], weights=[0.75, 0.25])[0]
    if rng.random() < 0.15:
        MONTHS = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December"]
        body, v = f"{d.day} {MONTHS[d.month - 1]} {d.year}", "text_en"
    else:
        body, v = fmt_date(d, rng, allow_partial=False)
    kind = "degree" if ring == "°" else "masc_ordinal"
    return f"{ring}{body}", f"{kind}_{v}"


def fmt_address(street: str, nr: str, rng) -> tuple[str, str]:
    v = rng.choices(
        ["plain", "box", "slash", "letter", "floor", "pobox"],
        weights=[0.50, 0.18, 0.09, 0.09, 0.08, 0.06])[0]
    if v == "plain":  return f"{street} {nr}", v
    if v == "box":    return f"{street} {nr} box {rng.randrange(1, 20)}", v
    if v == "slash":  return f"{street} {nr}/{rng.randrange(1, 20)}", v
    if v == "letter": return f"{street} {nr}{rng.choice('ABC')}", v
    if v == "floor":
        floor = rng.choice(["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor"])
        return f"{street} {nr}, {floor}", v
    return f"PO Box {rng.randrange(1, 999)}", v


def fmt_url(slug: str, rng: random.Random) -> tuple[str, str]:
    """Belgian hospital URL, matching every branch of the shared regex
    layer's URL pattern."""
    tld = rng.choices(["be", "com"], weights=[0.9, 0.1])[0]
    path = rng.choice(["", "", "/patient-portal", "/contact",
                       f"/appointment?id={rng.randrange(1000, 9999)}"])
    v = rng.choices(
        ["https_www", "http_www", "www_only", "https_bare", "bare"],
        weights=[0.42, 0.10, 0.20, 0.16, 0.12])[0]
    domain = f"www.{slug}.{tld}" if v in ("https_www", "http_www", "www_only") \
        else f"{slug}.{tld}"
    scheme = {"https_www": "https://", "http_www": "http://",
              "https_bare": "https://"}.get(v, "")
    return f"{scheme}{domain}{path}", v


# ===========================================================================
# Record
# ===========================================================================

@dataclass
class Case:
    case_id: str
    # --- stratification (evaluation slicing only, never a model output) ---
    sex: str
    age_band: str
    name_origin: str
    province: str
    region: str
    urbanicity: str
    # --- PII values, column name == template placeholder ---
    NAME_PATIENT: str = ""
    NAME_DOCTOR: str = ""
    NAME_RESPONSIBLE: str = ""
    NAME_DOCTOR_2: str = ""
    NAME_DOCTOR_3: str = ""
    NAME_DOCTOR_4: str = ""
    NAME_DOCTOR_5: str = ""
    NAME_DOCTOR_SENDER: str = ""
    NAME_RELATIVE: str = ""
    RELATIVE_RELATION: str = ""
    AGE: str = ""
    AGE_ADJ: str = ""
    GENDER: str = ""
    DATE_ENCOUNTER: str = ""
    DATE_VALIDATION: str = ""
    DATE_HISTORY: str = ""
    DOB: str = ""
    INSZ: str = ""
    RIZIV: str = ""
    INSZ_LABEL: str = ""    # non-PII: the literal lead-in phrase rendered
    RIZIV_LABEL: str = ""   # immediately before {INSZ}/{RIZIV} in every
                             # template -- sampled per-case from LABEL_POOL_*
                             # instead of hardcoded, so label-context variety
                             # is baked into 100% of the corpus from
                             # generation, not patched on afterward by
                             # augmentation. Never added to any label scheme,
                             # so render() substitutes but emits no span.
    IBAN: str = ""
    CREDITCARDNUMBER: str = ""
    STREET: str = ""
    ZIPCODE: str = ""
    CITY: str = ""
    TELEFOON: str = ""
    TELEFOON_MOBILE: str = ""
    EMAIL: str = ""
    URL: str = ""
    ORGANIZATION: str = ""
    # --- clinical context (not PII, but must be balanced) ---
    SPECIALTY: str = ""
    DIAGNOSIS: str = ""
    # hard negatives -- emitted into text, never labelled
    DX_EPONYM: str = ""
    DX_TEST: str = ""
    DX_ANATOMY: str = ""
    DX_DRUG: str = ""
    DX_DRUG_2: str = ""
    DX_HOMOGRAPH: str = ""
    DX_NUMERIC: str = ""
    DX_NUMERIC_2: str = ""
    DX_NUMERIC_3: str = ""
    DX_NUMERIC_4: str = ""
    DX_NUMERIC_5: str = ""
    DX_NUMERIC_6: str = ""
    DX_NUMERIC_7: str = ""
    DX_NUMERIC_8: str = ""
    DX_NUMERIC_9: str = ""
    DX_ABBREV: str = ""
    DX_CODESWITCH: str = ""
    DX_CNK: str = ""
    DX_CNK_2: str = ""
    DX_BELAC: str = ""
    noise_ops: str = ""
    ambiguous_surname: bool = False
    PATIENT_NOUN_GENERIC: str = ""     # always "patient" -- English has no
                                        # marked masculine/feminine form, so
                                        # unlike French/Dutch there is no
                                        # separate PATIENT_NOUN_MARKED field
                                        # at all (dropped, not just unused).
    HONORIFIC: str = ""
    PRONOUN_SUBJ: str = ""
    PRONOUN_POSS: str = ""             # SIMPLE per-case field for English
                                        # ("his"/"her" agree with the
                                        # POSSESSOR's sex, like Dutch
                                        # "zijn"/"haar") -- unlike French,
                                        # which had to drop this field
                                        # entirely because "son"/"sa" agree
                                        # with the POSSESSED noun's gender
                                        # instead. See module docstring.
    # --- provenance for per-format recall analysis ---
    fmt: dict = field(default_factory=dict)


def sample_origin(rng, weights=None):
    keys = list(NAMES)
    w = weights or [NAMES[k]["w"] for k in keys]
    return rng.choices(keys, weights=w)[0]


def build_case(i: int, rng: random.Random, fake: Faker,
               origin_weights=None, ref_date: date | None = None,
               cities=None,
               noise_rate: float = 0.0,
               ambiguous_rate: float = 0.08) -> Case:
    ref = ref_date or date(2026, 5, 28)
    cities = cities or BELGIAN_CITIES

    # --- balanced protected attributes ---
    sex = "M" if i % 2 == 0 else "F"                    # exact 50/50 by construction
    lo, hi, _ = rng.choices(AGE_BANDS, weights=[b[2] for b in AGE_BANDS])[0]
    age = rng.randrange(lo, hi + 1)
    origin = sample_origin(rng, origin_weights)

    birth = ref - timedelta(days=age * 365 + rng.randrange(0, 365))
    # Population-weighted city sampling across the whole country (nationally
    # distributed -- locked-in decision), NOT one region -- see
    # BELGIAN_CITIES module docstring for weight provenance.
    zipc, city, province, urban, region, _w = rng.choices(
        cities, weights=[c[5] for c in cities])[0]

    pool = NAMES[origin]
    given = rng.choice(pool["m" if sex == "M" else "f"])
    if rng.random() < ambiguous_rate:
        surname = rng.choice(DISTRACTORS["_ambiguous_surnames"])
        ambiguous = True
    else:
        surname = rng.choice(pool["s"])
        ambiguous = False
    patient = f"{given} {surname}"

    doc_origin = sample_origin(rng, origin_weights)
    docs = []
    for _ in range(6):
        o = NAMES[doc_origin]
        docs.append(rng.choice(o["s"]))          # surname only
        doc_origin = sample_origin(rng, origin_weights)
    ro = NAMES[sample_origin(rng, origin_weights)]
    responsible = f"{rng.choice(ro[rng.choice(['m','f'])])} {rng.choice(ro['s'])}"

    rp = NAMES[origin]
    RELATIONS = [("Mother", "f"), ("Father", "m"), ("Sister", "f"), ("Brother", "m"),
                 ("Daughter", "f"), ("Son", "m"), ("Aunt", "f"), ("Uncle", "m"),
                 ("Grandmother", "f"), ("Grandfather", "m"), ("Niece", "f"), ("Nephew", "m")]
    relation, rel_sex = rng.choice(RELATIONS)
    relative = f"{rng.choice(rp[rel_sex])} {rng.choice(rp['s'])}"

    pool_dx = [d for d in DIAGNOSES if d[2] is None or d[2] == sex]
    dx, specialty, _ = rng.choice(pool_dx)

    enc = ref - timedelta(days=rng.randrange(0, 45))
    val = enc + timedelta(days=rng.randrange(0, 3))
    hist = enc - timedelta(days=rng.randrange(200, 4000))

    org = (rng.choice(HOSPITAL_STANDALONE) if rng.random() < 0.55
           else f"{rng.choice(HOSPITAL_PREFIX)} {rng.choice(HOSPITAL_STEM)}")
    # A real hospital's URL is for the NETWORK, not the specific site -- so
    # "CHU de Liège - site Sart Tilman" should slug to "chudeliege", not the
    # full site-qualified name.
    org_network = org.split(" - ")[0]
    slug = (unicodedata.normalize("NFKD", org_network.lower())
            .encode("ascii", "ignore").decode()
            .replace(" ", "").replace("-", ""))

    insz_d = make_insz(birth, sex, rng)
    riziv_d = make_riziv(rng)
    iban_d = make_iban_be(rng)
    street = make_street(rng, region)
    nr = str(rng.randrange(1, 260))

    f = {}
    insz_s, f["INSZ"] = fmt_insz(insz_d, rng)
    riziv_s, f["RIZIV"] = fmt_riziv(riziv_d, rng)
    iban_s, f["IBAN"] = fmt_iban(iban_d, rng)
    enc_s, f["DATE_ENCOUNTER"] = fmt_date(enc, rng, allow_partial=False)
    val_s, f["DATE_VALIDATION"] = fmt_date(val, rng, allow_partial=False)
    hist_s, f["DATE_HISTORY"] = fmt_date(hist, rng, allow_partial=True)
    dob_s, f["DOB"] = fmt_dob_marker(birth, rng)
    tel_s, f["TELEFOON"], _ = make_phone(rng, "landline")
    mob_s, f["TELEFOON_MOBILE"], _ = make_phone(rng, "mobile")
    addr_s, f["STREET"] = fmt_address(street, nr, rng)
    url_s, f["URL"] = fmt_url(slug, rng)
    f["AGE"] = rng.choices(["aged", "years", "bare"], weights=[.5, .35, .15])[0]
    age_s = {"aged": f"aged {age}", "years": f"{age} years old", "bare": str(age)}[f["AGE"]]

    email_local = (unicodedata.normalize("NFKD", f"{given}.{surname}".lower())
                   .encode("ascii", "ignore").decode().replace(" ", ""))

    noise_log = ""
    if noise_rate > 0:
        ops = []
        for nm, val in [("NAME_PATIENT", patient), ("INSZ", insz_s),
                        ("TELEFOON", tel_s), ("STREET", addr_s),
                        ("DATE_ENCOUNTER", enc_s)]:
            new, op = inject_noise(val, rng, noise_rate)
            if op:
                ops.append(f"{nm}:{op}")
                if nm == "NAME_PATIENT": patient = new
                elif nm == "INSZ": insz_s = new
                elif nm == "TELEFOON": tel_s = new
                elif nm == "STREET": addr_s = new
                elif nm == "DATE_ENCOUNTER": enc_s = new
        noise_log = ";".join(ops)

    return Case(
        case_id=f"CASE{i:06d}",
        sex=sex,
        age_band=f"{lo}-{hi}",
        name_origin=origin,
        province=province,
        region=region,
        urbanicity=urban,
        NAME_PATIENT=patient,
        NAME_DOCTOR=f"Dr {docs[0]}",
        NAME_RESPONSIBLE=responsible,
        NAME_DOCTOR_2=f"Dr {docs[1]}",
        NAME_DOCTOR_3=f"Dr {docs[2]}",
        NAME_DOCTOR_4=f"Dr {docs[3]}",
        NAME_DOCTOR_5=f"Dr {docs[4]}",
        NAME_DOCTOR_SENDER=f"Dr {docs[5]}",
        NAME_RELATIVE=relative,
        RELATIVE_RELATION=relation,
        AGE=age_s,
        AGE_ADJ=f"{age} years old",
        GENDER="male" if sex == "M" else "female",
        DATE_ENCOUNTER=enc_s,
        DATE_VALIDATION=val_s,
        DATE_HISTORY=hist_s,
        DOB=dob_s,
        INSZ=insz_s,
        RIZIV=riziv_s,
        INSZ_LABEL=rng.choice(LABEL_POOL_INSZ),
        RIZIV_LABEL=rng.choice(LABEL_POOL_RIZIV),
        IBAN=iban_s,
        CREDITCARDNUMBER=luhn_card(rng),
        STREET=addr_s,
        ZIPCODE=zipc,
        CITY=city,
        TELEFOON=tel_s,
        TELEFOON_MOBILE=mob_s,
        EMAIL=f"{email_local}@{rng.choice(['gmail.com','outlook.com','hotmail.com','proximus.be','skynet.be','yahoo.com'])}",
        URL=url_s,
        ORGANIZATION=org,
        SPECIALTY=specialty,
        DIAGNOSIS=dx,
        DX_EPONYM=rng.choice(DISTRACTORS["eponym_disease"]),
        DX_TEST=rng.choice(DISTRACTORS["eponym_test"]),
        DX_ANATOMY=rng.choice(DISTRACTORS["anatomy_latin"]),
        DX_DRUG=rng.choice(DISTRACTORS["drug_brand"]),
        DX_DRUG_2=rng.choice(DISTRACTORS["drug_brand"]),
        DX_HOMOGRAPH=rng.choice(DISTRACTORS["municipality_homograph"]),
        DX_NUMERIC=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_2=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_3=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_4=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_5=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_6=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_7=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_8=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_NUMERIC_9=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_ABBREV=rng.choice(DISTRACTORS["abbreviation"]),
        DX_CODESWITCH=rng.choice(DISTRACTORS["code_switch"]),
        DX_CNK=rng.choice(DISTRACTORS["cnk_code"]),
        DX_CNK_2=rng.choice(DISTRACTORS["cnk_code"]),
        DX_BELAC=rng.choice(DISTRACTORS["belac_number"]),
        noise_ops=noise_log,
        ambiguous_surname=ambiguous,
        PATIENT_NOUN_GENERIC="patient",
        HONORIFIC="Mr" if sex == "M" else "Ms",
        PRONOUN_SUBJ="he" if sex == "M" else "she",
        PRONOUN_POSS="his" if sex == "M" else "her",
        fmt=f,
    )


# ===========================================================================
# Label schemes -- IDENTICAL to Dutch/French (locked-in decision, 2026-08-18:
# the annotation label taxonomy stays "INSZ"/"RIZIV"/etc across every
# language track, independent of what the in-document prose actually says).
# Keys are Case field names (language-agnostic), not language content.
# ===========================================================================

MERGED = {
    "NAME_PATIENT": "NAME", "NAME_DOCTOR": "NAME", "NAME_DOCTOR_2": "NAME",
    "NAME_DOCTOR_3": "NAME",
    "NAME_DOCTOR_4": "NAME",
    "NAME_DOCTOR_5": "NAME",
    "NAME_DOCTOR_SENDER": "NAME",
    "NAME_RELATIVE": "NAME", "AGE": "AGE", "AGE_ADJ": "AGE", "GENDER": "GENDER",
    "DATE_ENCOUNTER": "DATE", "DATE_VALIDATION": "DATE", "DATE_HISTORY": "DATE",
    "DOB": "DATE", "INSZ": "INSZ", "RIZIV": "RIZIV", "IBAN": "IBAN",
    "CREDITCARDNUMBER": "CREDITCARDNUMBER", "STREET": "STREET",
    "ZIPCODE": "ZIPCODE", "CITY": "CITY", "TELEFOON": "TELEFOON",
    "TELEFOON_MOBILE": "TELEFOON", "EMAIL": "EMAIL", "URL": "URL",
    "ORGANIZATION": "ORGANIZATION",
}
SPLIT = dict(MERGED, **{
    "NAME_PATIENT": "NAME_PATIENT", "NAME_DOCTOR": "NAME_DOCTOR", "NAME_RESPONSIBLE": "NAME_DOCTOR",
    "NAME_DOCTOR_2": "NAME_DOCTOR", "NAME_DOCTOR_3": "NAME_DOCTOR",
    "NAME_DOCTOR_4": "NAME_DOCTOR", "NAME_DOCTOR_5": "NAME_DOCTOR",
    "NAME_DOCTOR_SENDER": "NAME_DOCTOR", "NAME_RELATIVE": "NAME_RELATIVE",
    "DOB": "DOB",
})
FLAT9 = dict(MERGED, **{
    "NAME_RESPONSIBLE": "NAME",
    "ORGANIZATION": "NAME",
    "TELEFOON": "PHONE", "TELEFOON_MOBILE": "PHONE",
    "STREET": "ADDRESS", "ZIPCODE": "ADDRESS", "CITY": "ADDRESS",
})
SUBJECT = {
    "NAME_PATIENT": "patient", "NAME_DOCTOR": "provider",
    "NAME_DOCTOR_3": "provider",
    "NAME_DOCTOR_4": "provider",
    "NAME_DOCTOR_5": "provider",
    "NAME_DOCTOR_SENDER": "provider",
    "NAME_DOCTOR_2": "provider", "NAME_RELATIVE": "relative",
    "AGE": "patient", "AGE_ADJ": "patient", "DOB": "patient", "INSZ": "patient", "RIZIV": "provider",
    "IBAN": "patient", "CREDITCARDNUMBER": "patient", "STREET": "patient",
    "ZIPCODE": "patient", "CITY": "patient", "TELEFOON": "other",
    "TELEFOON_MOBILE": "patient", "EMAIL": "patient", "URL": "other",
    "ORGANIZATION": "other", "DATE_ENCOUNTER": "other",
    "DATE_VALIDATION": "other", "DATE_HISTORY": "patient", "GENDER": "patient",
    "NAME_RESPONSIBLE": "provider",
}


def render(template: str, case: Case, scheme=MERGED):
    """Fill {PLACEHOLDER} slots and return (text, annotations). Unchanged
    from Dutch/French -- language-agnostic mechanics."""
    d = asdict(case)
    out, spans, i = [], [], 0
    pos = 0
    import re as _re
    for m in _re.finditer(r"\{([A-Z_0-9]+)(?::(\d+))?\}", template):
        out.append(template[pos:m.start()])
        key, width = m.group(1), m.group(2)
        val = str(d.get(key, m.group(0)))
        start = sum(len(x) for x in out)
        out.append(val)
        if width:
            out.append(" " * max(0, int(width) - len(val)))
        if key in scheme:
            spans.append({
                "start": start, "end": start + len(val), "text": val,
                "label": scheme[key], "slot": key,
                "subject": SUBJECT.get(key, "other"),
                "fmt": case.fmt.get(key),
            })
        pos = m.end()
    out.append(template[pos:])
    return "".join(out), spans


DEMO_TEMPLATE = """LETTER

PATIENT: {NAME_PATIENT}          National Registration Number {INSZ}
RESPONSIBLE: {NAME_DOCTOR}   NIHDI number {RIZIV}
DATE: {DATE_ENCOUNTER}

Report contents
    {ORGANIZATION}
    {SPECIALTY}

    Dear colleague,

    We saw your {PATIENT_NOUN_GENERIC} {NAME_PATIENT} (born {DOB}), {AGE_ADJ},
    in {SPECIALTY} consultation on {DATE_ENCOUNTER}.
    Address: {STREET}, {ZIPCODE} {CITY}. Phone: {TELEFOON_MOBILE}.

    History:
    --------
    {DATE_HISTORY}: {DIAGNOSIS}
    {DX_EPONYM}! {DX_ABBREV}.

    Current treatment
    ------------------
    - {DX_DRUG}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1x/day, 08:00

    Clinical examination:
    ----------------------
    {DX_CODESWITCH}
    {DX_ANATOMY}: no lesion. {DX_HOMOGRAPH}.
    {DX_TEST}.

    Family history:
    ----------------
    {RELATIVE_RELATION} ({NAME_RELATIVE}): colorectal cancer at 60

    Conclusion:
    -----------
    Diagnosis: {DIAGNOSIS}. {PRONOUN_SUBJ} reports no new complaints;
    treatment is continued. Follow-up scheduled.

    Kind regards,
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    This report was electronically validated on {DATE_VALIDATION}
    {ORGANIZATION} | T {TELEFOON} | {EMAIL} | {URL}
"""


# ===========================================================================
# Audit -- UNCHANGED mechanism from Dutch/French. Statistical logic is
# language-agnostic; runs against whatever DataFrame it's given.
# ===========================================================================

def audit(df):
    import pandas as pd
    print("\n" + "=" * 72)
    print("FAIRNESS AUDIT")
    print("=" * 72)

    for col in ["sex", "age_band", "name_origin", "region", "province", "urbanicity"]:
        vc = df[col].value_counts(normalize=True).sort_index()
        print(f"\n{col}:")
        for k, v in vc.items():
            print(f"    {str(k):22s} {v:6.1%}  {'#' * int(v * 50)}")

    print("\nsex x diagnosis independence (sex-neutral diagnoses only):")
    import math
    sexed = {d[0] for d in DIAGNOSES if d[2]}
    sub = df[~df.DIAGNOSIS.isin(sexed)]
    ct = pd.crosstab(sub.DIAGNOSIS, sub.sex)
    ct["n"] = ct.sum(axis=1)
    ct["p_M"] = ct["M"] / ct["n"]
    ct["se"] = (0.25 / ct["n"]) ** 0.5
    ct["z"] = (ct["p_M"] - 0.5) / ct["se"]
    k = len(ct)
    crit = 2.5 if k < 5 else round(math.sqrt(2 * math.log(k)) + 1.0, 2)
    worst = ct.reindex(ct["z"].abs().sort_values(ascending=False).index).head(5)
    for dx, r in worst.iterrows():
        print(f"    {dx[:44]:46s} n={int(r['n']):4d}  p(M)={r['p_M']:.2f}  z={r['z']:+.2f}")
    mz = ct["z"].abs().max()
    print(f"    max |z| = {mz:.2f} over {k} diagnoses; critical ~{crit:.2f}  "
          f"({'OK -- consistent with sampling noise' if mz < crit else 'CHECK -- systematic'})")

    print("\nname_origin x diagnosis independence:")
    ct2 = pd.crosstab(df.name_origin, df.DIAGNOSIS, normalize="index")
    dev = (ct2 - ct2.mean(axis=0)).abs().max().max()
    print(f"    max cell deviation from marginal: {dev:.3f}  "
          f"({'OK' if dev < 0.06 else 'CHECK'})")

    print("\nINSZ parity vs sex (should be 1.00 by construction; "
          "this is a LEAK CHANNEL to test against, not a feature):")
    par = df.apply(lambda r: (int(str(r.INSZ).replace('.', '').replace(' ', '')
                                  .replace('-', '')[6:9]) % 2 == 1)
                             == (r.sex == "M"), axis=1)
    print(f"    consistent: {par.mean():.2%}")

    print("\nhard-negative coverage (must be tagged O, never labelled):")
    for col, key in [("DX_EPONYM", "eponym_disease"), ("DX_TEST", "eponym_test"),
                     ("DX_ANATOMY", "anatomy_latin"), ("DX_DRUG", "drug_brand"),
                     ("DX_HOMOGRAPH", "municipality_homograph"),
                     ("DX_NUMERIC", "numeric_lookalike"),
                     ("DX_CODESWITCH", "code_switch"), ("DX_CNK", "cnk_code"),
                     ("DX_BELAC", "belac_number")]:
        u = df[col].nunique()
        print(f"    {col:15s} {u:3d}/{len(DISTRACTORS[key]):3d} variants used, "
              f"rarest {df[col].value_counts(normalize=True).min():.1%}")
    amb = df.ambiguous_surname.astype(str).isin(["True", "true"]).mean()
    print(f"    ambiguous surnames (labelled NAME *and* appearing in eponyms): {amb:.1%}")
    nz = (df.noise_ops.fillna('') != '').mean()
    print(f"    char-noise rows: {nz:.1%}  "
          f"({'clean training set' if nz == 0 else 'normalizer TEST set'})")

    print("\nformat variant coverage (min share per label):")
    fm = pd.DataFrame(list(df.fmt))
    for c in ["INSZ", "TELEFOON", "DATE_ENCOUNTER", "DOB", "STREET"]:
        if c in fm:
            vc = fm[c].value_counts(normalize=True)
            print(f"    {c:16s} {len(vc)} variants, rarest {vc.min():.1%} ({vc.idxmin()})")

    print("\ncity sampling vs target population weight "
          "(checks the nationally-distributed weighted sampling actually works):")
    total_w = sum(c[5] for c in BELGIAN_CITIES)
    target = {c[1]: c[5] / total_w for c in BELGIAN_CITIES}
    observed = df["CITY"].value_counts(normalize=True) if "CITY" in df else None
    if observed is not None:
        worst_city = max(target, key=lambda c: abs(target[c] - observed.get(c, 0)))
        print(f"    max |target - observed| share: "
              f"{abs(target[worst_city] - observed.get(worst_city, 0)):.3f} "
              f"({worst_city})")


# ===========================================================================
# CLI
# ===========================================================================

def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="pii_table_en.csv")
    ap.add_argument("--jsonl", help="also write JSONL")
    ap.add_argument("--label-scheme", choices=["merged", "split", "flat9"], default="merged")
    ap.add_argument("--ambiguous-rate", type=float, default=0.08,
                    help="share of patients whose surname is also an eponym "
                         "test-name (Snellen, Graves...). 0 disables.")
    ap.add_argument("--noise-rate", type=float, default=0.0,
                    help="pre-normalization character corruption rate. "
                         "Use for TESTING the normalizer; keep 0 for training data.")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--origin-weights", help="comma list matching "
                    + ",".join(NAMES.keys()))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    Faker.seed(args.seed)
    fake = Faker("en_GB")

    ow = [float(x) for x in args.origin_weights.split(",")] if args.origin_weights else None
    cases = [build_case(i, rng, fake, ow, cities=BELGIAN_CITIES,
                        noise_rate=args.noise_rate,
                        ambiguous_rate=args.ambiguous_rate)
             for i in range(args.n)]
    df = pd.DataFrame([asdict(c) for c in cases])

    if args.demo:
        scheme = {"merged": MERGED, "split": SPLIT, "flat9": FLAT9}[args.label_scheme]
        text, spans = render(DEMO_TEMPLATE, cases[0], scheme)
        print(text)
        print("-" * 72)
        for s in spans[:14]:
            print(f"  [{s['start']:4d},{s['end']:4d}] {s['label']:16s} "
                  f"subj={s['subject']:9s} fmt={str(s['fmt']):12s} {s['text']!r}")
        print(f"  ... {len(spans)} spans total")
        return

    df.to_csv(args.out, index=False)
    print(f"wrote {len(df)} rows -> {args.out}")
    if args.jsonl:
        with open(args.jsonl, "w", encoding="utf-8") as fh:
            for c in cases:
                fh.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        print(f"wrote {args.jsonl}")

    if args.audit:
        audit(df)


if __name__ == "__main__":
    main()
