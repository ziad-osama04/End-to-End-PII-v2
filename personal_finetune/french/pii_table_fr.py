#!/usr/bin/env python3
"""
pii_table_fr.py -- generate a balanced synthetic PII value table for Walloon
(Belgian-French, NOT France-French) clinical-report templates.

Fork of TamerBERT/TamerBERT/pii_table.py (the Dutch/Flemish generator).
See personal_finetune/french/ in the repo for the fork rationale and the
overall French-track plan.

What changed vs. the Dutch original, and why
----------------------------------------------
Belgian-STRUCTURAL logic is UNCHANGED, because the French track is Belgian
(Walloon), not France -- INSZ/RIZIV/IBAN "BE" checksums and Belgian phone
area codes are national, not language-specific:
    make_insz, make_riziv, make_iban_be, luhn_card, fmt_insz, fmt_riziv,
    fmt_iban, make_phone, AGE_BANDS, NOISE_OPS, inject_noise, the
    MERGED/SPLIT/FLAT9/SUBJECT label-scheme dicts (keys are Case field
    names, not language content), render(), audit().

Everything else is a real Belgian-French fork, grounded in research rather
than translation, documented inline where the source matters:
  - WALLOON_CITIES: real Walloon + French-Brussels municipalities, each with
    a REAL population-derived sampling weight (Statbel-derived, 1 Jan 2024
    figures) -- so city sampling follows the actual Walloon population
    distribution, not uniform choice like the Dutch original. Brussels is
    deliberately capped at a small aggregate share (~8%) rather than fully
    population-weighted, mirroring the Dutch original's "small share"
    design intent (a French-Belgian PII dataset should mostly look like
    Wallonia, with a French-speaking-Brussels minority, not literally
    proportional to Brussels' full population).
  - Street naming: French/Walloon addresses do NOT compound into one word
    the way Dutch does (Kerkstraat) -- they follow "[voie-type] + de/du/des
    + [theme]" (e.g. "Rue de la Gare"). make_street_fr() replaces the old
    stem+suffix concatenation with this real pattern.
  - NAMES: "flemish" origin renamed "walloon" with real French-Belgian
    given/family names. Origin WEIGHTS are re-derived from real Wallonia
    demographics (Statbel/IWEPS), not copied from the Flemish weights:
    southern_european (Italian-dominant, 1946 labor-migration wave into the
    Liege/Charleroi mining basins) is weighted much higher than the Flemish
    list's 0.08; turkish is weighted lower (Turkish immigration in Belgium
    concentrated in Flanders/Brussels, not Wallonia). See the NAMES block
    below for the exact reasoning per origin.
  - SPECIALTIES/DIAGNOSES: medically-verified French clinical terminology
    (not machine translation) -- e.g. "polyarthrite rhumatoide" not the
    anglicism-calque "arthrite rhumatoide"; Belgian-specific drug-notice
    spelling kept where it's a genuine BE/FR difference (Ventolin not
    Ventoline, Nexiam not Inexium).
  - HOSPITAL_*: real Walloon hospital networks/names (CHU/CHR/CHC/CHwapi/
    Vivalia/Clinique) from AVIQ's official registry, not invented.
  - DISTRACTORS: French clinical abbreviations, French-Latin anatomy
    convention (French adjective + Latin genus abbreviation, e.g.
    "m. sous-epineux" not a bare Latin binomial), and a SMALLER starter set
    of municipality homographs than the Dutch original (Marche=gait,
    Bouillon=broth/culture-medium, Mons pubis, Ath embedded in "catheter")
    -- this is flagged as an intentionally incomplete starter set; finding
    more real Walloon-municipality/French-word homographs is exactly the
    kind of thing a real OOD discovery pass should expand, not something to
    force-fit speculatively up front.
  - IMPORTANT LINGUISTIC CATCH, not present in the Dutch original: Dutch
    "zijn"/"haar" (his/her) mark the POSSESSOR's gender directly, so a
    single per-case PRONOUN_POSS slot works. French "son"/"sa" agree with
    the GENDER OF THE NOUN BEING POSSESSED, not the possessor's sex ("son
    traitement" is masculine because "traitement" is masculine, regardless
    of patient sex; "sa maladie" is feminine because "maladie" is feminine,
    again regardless of patient sex). A single PRONOUN_POSS Case field
    would therefore be WRONG for French. This field is deliberately DROPPED
    here; templates must hardcode "son"/"sa" directly, matching whichever
    specific noun follows in that specific sentence, at translation time.
    PRONOUN_SUBJ ("il"/"elle") has no such problem -- subject pronouns for
    a human referent agree with the person's own gender -- and is kept.

Usage
    python3 pii_table_fr.py -n 2000 --out pii_table_fr.csv --audit
    python3 pii_table_fr.py -n 500 --label-scheme split --out split.csv
    python3 pii_table_fr.py --demo            # show one filled template
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
# Reference data: Belgium / Wallonia
# ===========================================================================

# (zipcode, city, province, urbanicity, region, weight). Zip and city always
# travel together. weight is a REAL population-derived sampling weight
# (Statbel-derived figures, 1 Jan 2024) for the 35 Walloon entries; the 5
# Brussels-Capital (French-speaking) entries are deliberately down-scaled so
# Brussels sums to ~8% of total sampling weight rather than its true (much
# larger) population share -- see module docstring for why.
WALLOON_CITIES = [
    # --- Liège ---
    ("4000", "Liège",                 "Liège", "urban", "Wallonie", 197013),
    ("4100", "Seraing",               "Liège", "urban", "Wallonie", 63968),
    ("4040", "Herstal",               "Liège", "town",  "Wallonie", 39242),
    ("4800", "Verviers",              "Liège", "urban", "Wallonie", 56594),
    ("4500", "Huy",                   "Liège", "town",  "Wallonie", 21354),
    ("4300", "Waremme",               "Liège", "town",  "Wallonie", 14789),
    ("4970", "Stavelot",              "Liège", "rural", "Wallonie", 6919),

    # --- Namur ---
    ("5000", "Namur",                 "Namur", "urban", "Wallonie", 110691),
    ("5300", "Andenne",               "Namur", "town",  "Wallonie", 25729),
    ("5030", "Gembloux",              "Namur", "town",  "Wallonie", 24206),
    ("5500", "Dinant",                "Namur", "town",  "Wallonie", 13912),
    ("5590", "Ciney",                 "Namur", "rural", "Wallonie", 15670),
    ("5580", "Rochefort",             "Namur", "rural", "Wallonie", 12515),
    ("5600", "Philippeville",         "Namur", "rural", "Wallonie", 9089),

    # --- Hainaut ---
    ("6000", "Charleroi",             "Hainaut", "urban", "Wallonie", 204670),
    ("7000", "Mons",                  "Hainaut", "urban", "Wallonie", 93366),
    ("7500", "Tournai",               "Hainaut", "urban", "Wallonie", 69751),
    ("7100", "La Louvière",           "Hainaut", "town",  "Wallonie", 78895),
    ("7700", "Mouscron",              "Hainaut", "town",  "Wallonie", 56023),
    ("7800", "Ath",                   "Hainaut", "town",  "Wallonie", 28543),
    ("7060", "Soignies",              "Hainaut", "rural", "Wallonie", 26536),
    ("6460", "Chimay",                "Hainaut", "rural", "Wallonie", 9896),

    # --- Luxembourg ---
    ("6700", "Arlon",                 "Luxembourg", "town",  "Wallonie", 29733),
    ("6600", "Bastogne",              "Luxembourg", "town",  "Wallonie", 15127),
    ("6900", "Marche-en-Famenne",     "Luxembourg", "town",  "Wallonie", 17454),
    ("6800", "Libramont-Chevigny",    "Luxembourg", "rural", "Wallonie", 12084),
    ("6840", "Neufchâteau",           "Luxembourg", "rural", "Wallonie", 7284),
    ("6760", "Virton",                "Luxembourg", "rural", "Wallonie", 11670),
    ("6830", "Bouillon",              "Luxembourg", "rural", "Wallonie", 5426),

    # --- Brabant Wallon ---
    ("1300", "Wavre",                        "Brabant Wallon", "town",  "Wallonie", 33277),
    ("1400", "Nivelles",                     "Brabant Wallon", "town",  "Wallonie", 26843),
    ("1340", "Ottignies-Louvain-la-Neuve",   "Brabant Wallon", "urban", "Wallonie", 31190),
    ("1420", "Braine-l'Alleud",              "Brabant Wallon", "town",  "Wallonie", 40461),
    ("1495", "Genappe",                      "Brabant Wallon", "rural", "Wallonie", 15137),
    ("1370", "Jodoigne",                     "Brabant Wallon", "rural", "Wallonie", 13612),

    # --- Brussels-Capital (French-speaking share, weight deliberately
    #     down-scaled -- see module docstring) ---
    ("1000", "Bruxelles",             "Bruxelles-Capitale", "urban", "Bruxelles-Capitale", 57879),
    ("1050", "Ixelles",               "Bruxelles-Capitale", "urban", "Bruxelles-Capitale", 26772),
    ("1060", "Saint-Gilles",          "Bruxelles-Capitale", "urban", "Bruxelles-Capitale", 15560),
    ("1190", "Forest",                "Bruxelles-Capitale", "town",  "Bruxelles-Capitale", 17116),
    ("1170", "Watermael-Boitsfort",   "Bruxelles-Capitale", "town",  "Bruxelles-Capitale", 7779),
]

# Real Walloon hospital naming, from AVIQ's official registry (36 general +
# 4 university hospitals, ~75 sites) plus the French-speaking Brussels IRIS
# network. Structured to mirror the Dutch PREFIX+STEM / STANDALONE split,
# but grounded in actual institutions rather than a generic template --
# French-Belgian hospital naming is less "compositional" than Flemish
# AZ+stem, so STANDALONE carries more of the weight here.
HOSPITAL_PREFIX = ["CHU", "CHR", "CHC", "Clinique", "Hôpital", "Centre Hospitalier"]
HOSPITAL_STEM = [
    "Saint-Pierre", "Saint-Luc", "Saint-Joseph", "Sainte-Élisabeth",
    "Notre-Dame", "Sainte-Thérèse", "Reine Fabiola", "Reine Astrid",
    "Waremme", "Citadelle", "Ambroise Paré",
]
# Near-exhaustive: AVIQ's official count is 36 general + 4 university
# hospitals across ~75 sites in Wallonia alone; this list enumerates real
# named sites (not just network/group names) across all 5 Walloon provinces
# plus the French-speaking Brussels IRIS/CHIREC network, sourced from AVIQ's
# registry, Wikipedia's "Liste des hopitaux belges", and individual network
# sites (chuliege.be, vivalia.be, chwapi.be, ghdc.be, etc). German-speaking-
# Community hospitals (Eupen, Sankt-Vith) are excluded -- out of scope for a
# French-Belgian, not German-Belgian, generator. Psychiatric/specialized
# sites ARE included: real referral/discharge letters do reference them, and
# excluding them would silently narrow ORGANIZATION's real-world range.
HOSPITAL_STANDALONE = [
    # --- Liège ---
    "CHU de Liège - site Sart Tilman", "CHU de Liège - site Notre-Dame des Bruyères",
    "CHU de Liège - site Ourthe-Amblève", "CHR de la Citadelle", "CHC MontLégia",
    "CHC Heusy", "CHC Waremme", "CHC Hermalle", "Centre Hospitalier Bois de l'Abbaye",
    "CHR Huy", "CHR Verviers", "Clinique André Renard", "Hôpital du Valdor",
    "CHR Reine Astrid de Malmédy", "Foyer Horizon",
    "Centre Hospitalier Spécialisé L'Accueil",
    "Centre Hospitalier Spécialisé Notre-Dame des Anges",
    # --- Namur ---
    "CHU UCL Namur - site Sainte-Élisabeth", "CHU UCL Namur - site Godinne",
    "CHU UCL Namur - site Dinant", "Clinique Saint-Luc de Bouge",
    "CHR Val de Sambre - site Sambreville", "CHR Val de Sambre - site Fosses-la-Ville",
    "Foyer Saint-François", "Hôpital psychiatrique du Beau Vallon",
    "Centre neuropsychiatrique Saint-Martin",
    "Centre de psychiatrie infantile Les Goélands",
    # --- Hainaut ---
    "Grand Hôpital de Charleroi - site Notre-Dame",
    "Grand Hôpital de Charleroi - site Saint-Joseph",
    "Grand Hôpital de Charleroi - site Sainte-Thérèse",
    "Grand Hôpital de Charleroi - site IMTR",
    "Grand Hôpital de Charleroi - site Reine Fabiola",
    "CHU Charleroi - Hôpital civil Marie Curie", "CHU Charleroi - Hôpital André Vésale",
    "Clinique Notre-Dame de Grâce", "Centre de Santé des Fagnes", "CHU Ambroise Paré",
    "Centre Hospitalier Régional Mons-Hainaut", "Centre Hospitalier EpiCURA - site Ath",
    "Centre Hospitalier EpiCURA - site Baudour", "Centre Hospitalier EpiCURA - site Hornu",
    "CHwapi - site Union", "CHwapi - site Notre-Dame", "CHwapi - site IMC",
    "CHU Tivoli", "Hôpital de Jolimont", "Hôpital de Lobbes",
    "Centre Hospitalier de Mouscron", "Centre Hospitalier Régional de la Haute Senne",
    "Clinique de Bonsecours", "Centre Régional Psychiatrique Les Marronniers",
    "Hôpital psychiatrique Saint-Bernard", "Hôpital psychiatrique Saint-Jean-de-Dieu",
    "Centre Hospitalier Psychiatrique Le Chêne aux Haies",
    # --- Luxembourg (Vivalia network) ---
    "Vivalia - Hôpital d'Arlon", "Vivalia - Hôpital de Virton",
    "Vivalia - Hôpital de Bastogne", "Vivalia - Hôpital de Marche",
    "Vivalia - Hôpital de Libramont", "Vivalia - Polyclinique Saint-Gengoux",
    "Vivalia - Hôpital psychiatrique La Clairière",
    # --- Brabant Wallon ---
    "Clinique Saint-Pierre Ottignies", "Cliniques universitaires de Mont-Godinne",
    "Hôpital de Nivelles", "Hôpital de Braine-l'Alleud - Waterloo",
    "Clinique du Bois de la Pierre", "Centre Hospitalier Neurologique William Lennox",
    "Centre Hospitalier Le Domaine", "La Petite Maison",
    # --- Brussels (IRIS network, CHIREC, and university hospitals) ---
    "CHU Saint-Pierre", "CHU Brugmann", "HUDERF", "Institut Jules Bordet",
    "Hôpitaux Iris Sud - site Etterbeek-Ixelles",
    "Hôpitaux Iris Sud - site Molière-Longchamp",
    "Hôpitaux Iris Sud - site Joseph Bracops", "Hôpitaux Iris Sud - site Baron Lambert",
    "Cliniques universitaires Saint-Luc", "Hôpital Erasme", "CHIREC - Hôpital Delta",
    "CHIREC - Clinique Sainte-Anne-Saint-Rémi", "CHIREC - Clinique Basilique",
    "Cliniques de l'Europe",
]

# French/Walloon street naming does NOT compound into one word (Dutch
# "Kerkstraat"); it is "[voie-type] de/du/des/de la [theme]". See module
# docstring for source (a linguistic breakdown of ~62k Francophone-Belgian
# street names).
STREET_TYPE = [
    "Rue", "Chemin", "Avenue", "Place", "Clos", "Route", "Allée",
    "Chaussée", "Ruelle", "Impasse", "Drève", "Boulevard", "Square", "Quai",
]
STREET_THEME = [
    "de la Gare", "du Moulin", "des Champs", "de l'Église", "du Château",
    "de la Fontaine", "du Pont", "de la Chapelle", "des Écoles",
    "de la Station", "de la Croix", "des Tilleuls", "du Chêne",
    "des Marronniers", "des Bouleaux", "du Bois", "de la Prairie",
    "des Prés", "Saint-Roch", "Sainte-Anne", "Saint-Nicolas", "Saint-Hubert",
    "Sainte-Barbe", "de la Vallée", "de l'Étang", "de la Meuse",
    "de la Sambre", "des Tanneurs", "du Marché", "de Namur", "de Charleroi",
    "de Bruxelles", "de Liège", "de Mons", "de Tournai", "de Nivelles",
    "Albert Ier", "de la Liberté",
]


def make_street_fr(rng: random.Random) -> str:
    return f"{rng.choice(STREET_TYPE)} {rng.choice(STREET_THEME)}"


# Name pools stratified by origin. Weights are re-derived from real
# Wallonia demographics (Statbel "Diversity according to origin in
# Belgium", IWEPS Jan-2025 foreign-nationals breakdown), NOT copied from
# the Flemish weights:
#   - walloon (main pool): Statbel puts Belgian-background share in
#     Wallonia at ~63-67%; French nationals (the single largest EU foreign
#     group in Wallonia, ~21% of foreign nationals) are folded into this
#     bucket rather than given their own category, since they're not
#     distinguishable by name -- same reasoning the Dutch original used to
#     justify having no separate "Dutch" bucket.
#   - southern_european: raised well above the Flemish list's 0.08. Statbel
#     confirms Italian as the SINGLE LARGEST origin group in Wallonia (the
#     1946 Belgo-Italian labor-migration protocol into the Liège/Charleroi
#     "Pays Noir" mining basins) -- this is Wallonia's most distinctive
#     demographic difference from Flanders.
#   - maghrebi: kept comparable to the Flemish weight -- Morocco is
#     confirmed as Wallonia's third-largest origin group (~18k foreign
#     nationals, IWEPS), a similar order of magnitude to Flanders.
#   - turkish: lowered from the Flemish 0.06. Turkish immigration in
#     Belgium is documented as concentrated in Flemish industrial cities
#     (Genk, Ghent) and Brussels, much less so in Wallonia.
#   - central_african: kept comparable to Flemish. Congolese/Rwandan/
#     Burundian population is documented as concentrated mainly in
#     Brussels, with Liège as a secondary hub from colonial-era
#     university/administrative ties -- no precise Wallonia-only figure
#     exists, so this is a reasoned estimate, not a directly sourced one.
#   - eastern_european: kept close to Flemish, if anything slightly higher
#     -- IWEPS documents a large recent increase in Ukrainian nationals in
#     Wallonia (921 -> 12,853 between Jan-2022 and Jan-2025).
NAMES = {
    "walloon": {
        "w": 0.60,
        "m": ["Jean", "Pierre", "Marc", "Michel", "Nicolas", "Vincent",
              "Julien", "Olivier", "Laurent", "Benoît", "Thomas", "Xavier",
              "Fabrice", "Yves", "Christophe", "Guillaume", "Damien", "Denis"],
        "f": ["Marie", "Sophie", "Catherine", "Anne", "Isabelle", "Nathalie",
              "Julie", "Caroline", "Valérie", "Céline", "Aurélie", "Laëtitia",
              "Charlotte", "Camille", "Delphine", "Manon", "Émilie", "Sarah"],
        "s": ["Dubois", "Lambert", "Simon", "Léonard", "Georges", "Renard",
              "Collard", "Delcourt", "Herman", "Fontaine", "Gérard", "Michel",
              "Marchal", "Toussaint", "Lejeune", "Dupont", "Thomas", "Nicolas",
              "Bertrand", "Servais", "Halleux", "Delvaux"],
    },
    "southern_european": {
        "w": 0.15,
        "m": ["Marco", "Giuseppe", "Antonio", "Salvatore", "Vincenzo",
              "Angelo", "Rafael", "Miguel", "Bruno", "Mario"],
        "f": ["Maria", "Giulia", "Rosa", "Carmela", "Ana", "Sofia", "Elena",
              "Lucia", "Concetta", "Assunta"],
        "s": ["Rossi", "Esposito", "Ferrari", "Romano", "Silva", "Santos",
              "Garcia", "Fernandez", "Costa", "Moreira", "Greco", "Bruno",
              "Marino", "Ricci"],
    },
    "maghrebi": {
        "w": 0.10,
        "m": ["Mohamed", "Youssef", "Karim", "Bilal", "Rachid", "Hamza",
              "Anas", "Ismail", "Adil", "Nabil", "Yassine", "Mehdi"],
        "f": ["Fatima", "Amina", "Khadija", "Nadia", "Samira", "Sara",
              "Leila", "Yasmine", "Meryem", "Hafida", "Ilham"],
        "s": ["El Amrani", "Benali", "Ouazzani", "Cherkaoui", "El Habti",
              "Bouzid", "Rahmani", "Idrissi", "El Fassi", "Bennani", "Alaoui"],
    },
    "central_african": {
        "w": 0.05,
        "m": ["Patrick", "Christian", "Emmanuel", "Joseph", "Didier",
              "Gaston", "Serge", "Blaise"],
        "f": ["Grace", "Esther", "Nadine", "Chantal", "Mireille", "Sylvie",
              "Bernadette", "Josiane"],
        "s": ["Mbala", "Kabongo", "Ilunga", "Nkosi", "Mukendi", "Tshibangu",
              "Lumumba", "Kalala", "Mwamba", "Bope"],
    },
    "eastern_european": {
        "w": 0.10,
        "m": ["Piotr", "Andrzej", "Tomasz", "Ionut", "Vasile", "Dimitar",
              "Miroslav", "Krzysztof", "Oleksandr", "Dmytro"],
        "f": ["Agnieszka", "Katarzyna", "Magdalena", "Ioana", "Elena",
              "Svetlana", "Zuzana", "Iwona", "Olena", "Kateryna"],
        "s": ["Kowalski", "Nowak", "Wisniewski", "Popescu", "Ionescu",
              "Dimitrov", "Novak", "Zielinski", "Kaminski", "Marinescu",
              "Kovalenko", "Shevchenko"],
    },
}

SPECIALTIES = [
    "Gastro-entérologie", "Médecine physique et réadaptation", "Ophtalmologie",
    "Pneumologie", "Cardiologie", "Neurologie", "Dermatologie", "Endocrinologie",
    "Néphrologie", "Orthopédie", "Urologie", "Gynécologie", "Rhumatologie",
    "Oncologie", "ORL", "Gériatrie", "Chirurgie vasculaire", "Chirurgie générale",
]

# (diagnosis, specialty, sex_restriction) -- sex_restriction None = either.
# French translations verified against Belgian clinical usage, not machine
# translation -- see module docstring for the two calque traps avoided
# (polyarthrite rhumatoide not "arthrite rhumatoide"; Belgian drug-notice
# spelling kept where genuinely BE-specific).
DIAGNOSES = [
    ("fissure anale",                                "Gastro-entérologie", None),
    ("colite chronique non spécifique légère",       "Gastro-entérologie", None),
    ("ulcère anastomotique",                         "Gastro-entérologie", None),
    ("anémie ferriprive",                            "Gastro-entérologie", None),
    ("status post bypass gastrique (RYGB)",          "Gastro-entérologie", None),
    ("œsophagite de reflux, grade B",                "Gastro-entérologie", None),
    ("diverticulose sigmoïdienne",                   "Gastro-entérologie", None),
    ("maladie cœliaque",                             "Gastro-entérologie", None),
    ("épididymite gauche",                           "Urologie",           "M"),
    ("tendinose bilatérale du tendon sus-épineux",   "Médecine physique et réadaptation", None),
    ("bursite sous-acromiale",                       "Médecine physique et réadaptation", None),
    ("hypertonie du plancher pelvien",               "Médecine physique et réadaptation", None),
    ("épicondylite latérale droite",                 "Médecine physique et réadaptation", None),
    ("syndrome facettaire lombaire",                 "Médecine physique et réadaptation", None),
    ("absence de rétinopathie diabétique",           "Ophtalmologie",       None),
    ("cataracte débutante bilatérale",               "Ophtalmologie",       None),
    ("glaucome à angle ouvert",                      "Ophtalmologie",       None),
    ("dégénérescence maculaire liée à l'âge de forme sèche", "Ophtalmologie", None),
    ("bronchopneumopathie chronique obstructive, stade GOLD II", "Pneumologie", None),
    ("asthme bien contrôlé",                         "Pneumologie",        None),
    ("syndrome d'apnées obstructives du sommeil",    "Pneumologie",        None),
    ("maladie de Von Willebrand",                    "Chirurgie générale", None),
    ("épilepsie en rémission",                       "Neurologie",         None),
    ("migraine avec aura",                           "Neurologie",         None),
    ("polyneuropathie périphérique",                 "Neurologie",         None),
    ("diabète de type 2",                            "Endocrinologie",     None),
    ("hypothyroïdie",                                "Endocrinologie",     None),
    ("ostéoporose",                                  "Rhumatologie",       None),
    ("polyarthrite rhumatoïde",                      "Rhumatologie",       None),
    ("fibrillation auriculaire",                     "Cardiologie",        None),
    ("hypertension artérielle",                      "Cardiologie",        None),
    ("insuffisance rénale chronique stade 3",        "Néphrologie",        None),
    ("gonarthrose bilatérale",                       "Orthopédie",         None),
    ("syndrome du canal carpien",                    "Orthopédie",         None),
    ("hyperplasie bénigne de la prostate",           "Urologie",           "M"),
    ("endométriose",                                 "Gynécologie",        "F"),
    ("utérus myomateux",                             "Gynécologie",        "F"),
    ("eczéma atopique",                              "Dermatologie",       None),
    ("psoriasis vulgaire",                           "Dermatologie",       None),
    ("rhinosinusite chronique",                      "ORL",                None),
]

AGE_BANDS = [(0, 17, 0.06), (18, 34, 0.16), (35, 49, 0.19),
             (50, 64, 0.24), (65, 79, 0.24), (80, 95, 0.11)]


# ===========================================================================
# HARD NEGATIVES
# These are strings that LOOK like PII and must be tagged O. Same rationale
# as the Dutch original: without them the model never learns to reject a
# municipality name embedded in an ordinary word.
# ===========================================================================

DISTRACTORS = {
    "eponym_disease": [
        "maladie de Von Willebrand", "maladie de Crohn", "maladie de Parkinson",
        "syndrome de Sjögren", "syndrome de Raynaud", "maladie de Graves",
        "maladie de Bechterew", "syndrome de Guillain-Barré",
        "signe de Lasègue", "manœuvre de Valsalva", "maladie de Hashimoto",
        "syndrome de Cushing", "maladie de Dupuytren",
    ],
    "eponym_test": [
        "test de Snellen", "test de Humphrey", "test de Jaeger",
        "applanation de Goldmann", "test de Schirmer", "signe de Tinel",
        "manœuvre de Phalen", "Romberg négatif", "échelle de Glasgow 15",
        "index de Barthel 90", "échelle de Bristol type 4",
    ],
    # French clinical convention: French adjective + Latin genus
    # abbreviation, NOT a bare Latin binomial (verified -- see module
    # docstring). Both "traditional" and "modern PNA" nomenclature kept,
    # since real Belgian reports mix both depending on the author's era.
    "anatomy_latin": [
        "le long biceps (LB)", "m. sous-épineux", "m. supra-épineux",
        "m. sus-épineux", "m. infra-épineux", "n. médian", "a. radiale",
        "lig. collatéral médial", "v. saphène magna",
    ],
    # Belgium registers medicines nationally -- brand names are identical
    # across language communities (confirmed via CBIP/e-compendium.be), so
    # this list is largely unchanged from the Dutch original except unit
    # abbreviation "ie" (Dutch "internationale eenheden") -> "UI" (French
    # "unités internationales").
    "drug_brand": [
        "Asaflow 80 mg", "Atorstatine 20 mg", "D-cure 25 000 UI",
        "GlucaGen hypokit", "Lyumjev kwikpen", "Toujeo solostar",
        "Lambipol 100 mg", "L-thyroxine 50 mcg", "Metformine viatris 500 mg",
        "Nexiam 20 mg", "Ozempic 1 mg", "Progor retard 180 mg",
        "Sipralexa 20 mg", "Depakine chrono 500 mg", "Pantomed 40 mg",
        "Injectafer 1000 mg", "Ventolin aerosol", "Diltiazem gel 2%",
        "Cose protect", "Trianal suppo", "Ibuprofen 400 mg", "Paracetamol 1 g",
    ],
    # Real Walloon municipality names embedded in, or identical to, ordinary
    # French words -- the same class that broke the Dutch incumbent tool
    # (Asse inside "passend"). DELIBERATELY A SMALLER STARTER SET than the
    # Dutch original's 9: finding real French-word/Walloon-municipality
    # collisions is genuinely hard (most Walloon place names have no French
    # common-word homograph), and force-fitting weak near-matches would be
    # worse than an honest, expandable starter set. Expanding this list is
    # exactly the kind of thing a real OOD discovery pass on real French
    # text should drive, not something to guess exhaustively up front.
    "municipality_homograph": [
        "reprise de la marche sans aide",          # Marche (-en-Famenne)
        "bouillon de culture positif",             # Bouillon
        "examen du mons pubis sans particularité", # Mons
        "pose d'un cathéter sous-clavier",         # Ath (embedded: c-ATH-éter)
    ],
    "numeric_lookalike": [
        "1x/j", "2x/j", "1x/sem", "3x/semaine", "1 à 2 /j", "8h", "12h",
        "18h", "22h", "TA: 146/68", "FC: 68", "SpO2: 94%", "2cc", "3x",
        "25 000 UI", "100 e/ml 3 ml", "300 UI/ml 1.5 ml", "0.5 mg", "4.95*",
        "-0.25 ^ -0.25 axe 165 degrés", "FEV1/FVC 73.17", "BMI 20.808",
        "T 37.2", "pH 7.38", "J+7", "J15",
    ],
    # Real French/Belgian clinical abbreviations, verified against Belgian
    # medical-abbreviation references. "tvv"/"co" from the Dutch original
    # have no standardized 1:1 French abbreviation (French doctors spell
    # these out) so they are NOT force-translated here -- see module
    # docstring.
    "abbreviation": [
        "ATCD", "RAS", "TTT", "SP", "AEG", "EG", "MT", "PRN", "s/p",
    ],
    # Surnames that are ALSO eponyms/test names. These are international
    # proper nouns (not Dutch-specific to begin with), so ported unchanged.
    "_ambiguous_surnames": [
        "Snellen", "Jaeger", "Graves", "Romberg", "Phalen", "Goldmann",
        "Schirmer", "Tinel", "Bristol", "Barthel",
    ],
    # English inside French prose: the code-switch fragments are English
    # regardless of the base language, so this list is unchanged from Dutch.
    "code_switch": [
        "Painful arc bilatéral +", "blurr-test", "SSp testing positive",
        "full range of motion", "no evidence of malignancy",
        "watchful waiting", "shared decision making",
    ],
}


# ---------------------------------------------------------------------------
# Character-level noise: simulates PRE-normalization text. Unchanged from
# Dutch original -- pure Unicode-level, language-agnostic.
# ---------------------------------------------------------------------------

NOISE_OPS = {
    "nbsp":        lambda s, r: s.replace(" ", "\u00a0", 1) if " " in s else s,
    "narrow_nbsp": lambda s, r: s.replace(" ", "\u202f", 1) if " " in s else s,
    "soft_hyphen": lambda s, r: (s[:len(s)//2] + "\u00ad" + s[len(s)//2:]
                                 if len(s) > 8 else s),
    "zwsp":        lambda s, r: (s[:len(s)//2] + "\u200b" + s[len(s)//2:]
                                 if len(s) > 8 else s),
    "curly_quote": lambda s, r: s.replace("'", "\u2019"),
    "en_dash":     lambda s, r: s.replace("-", "\u2013", 1) if "-" in s else s,
    "nb_hyphen":   lambda s, r: s.replace("-", "\u2011", 1) if "-" in s else s,
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
# Belgian identifier construction (real checksums) -- UNCHANGED from the
# Dutch original. These are national Belgian formats, not language-bound.
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
    language-independent, unchanged from the Dutch original."""
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
    MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]
    yy = d.year % 100
    opts = ["dd/mm/yyyy", "dd-mm-yyyy", "dd.mm.yyyy", "d/m/yyyy",
            "yyyy-mm-dd", "text_fr", "text_abbr",
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
        "text_fr":    f"{d.day} {MONTHS[d.month-1]} {d.year}",
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
    """The Belgian birth marker. Occasionally uses the French text-month
    form instead of a numeric date."""
    ring = rng.choices(["\u00b0", "\u00ba"], weights=[0.75, 0.25])[0]
    if rng.random() < 0.15:
        MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin",
                  "juillet", "août", "septembre", "octobre", "novembre",
                  "décembre"]
        body, v = f"{d.day} {MONTHS[d.month - 1]} {d.year}", "text_fr"
    else:
        body, v = fmt_date(d, rng, allow_partial=False)
    kind = "degree" if ring == "\u00b0" else "masc_ordinal"
    return f"{ring}{body}", f"{kind}_{v}"


def fmt_address(street: str, nr: str, rng) -> tuple[str, str]:
    v = rng.choices(
        ["plain", "bus", "slash", "letter", "floor", "postbus"],
        weights=[0.50, 0.18, 0.09, 0.09, 0.08, 0.06])[0]
    if v == "plain":  return f"{street} {nr}", v
    if v == "bus":    return f"{street} {nr} boîte {rng.randrange(1, 20)}", v
    if v == "slash":  return f"{street} {nr}/{rng.randrange(1, 20)}", v
    if v == "letter": return f"{street} {nr}{rng.choice('ABC')}", v
    if v == "floor":
        floor = rng.choice(["rez-de-chaussée", "1er", "2e", "3e", "4e"])
        return f"{street} {nr}, {floor} étage", v
    return f"Boîte postale {rng.randrange(1, 999)}", v


def fmt_url(slug: str, rng: random.Random) -> tuple[str, str]:
    """Belgian hospital URL, matching every branch of the shared regex
    layer's URL pattern."""
    tld = rng.choices(["be", "com"], weights=[0.9, 0.1])[0]
    path = rng.choice(["", "", "/espace-patient", "/contact",
                       f"/rendez-vous?id={rng.randrange(1000, 9999)}"])
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
    DX_ABBREV: str = ""
    DX_CODESWITCH: str = ""
    noise_ops: str = ""
    ambiguous_surname: bool = False
    PATIENT_NOUN_GENERIC: str = ""     # template boilerplate: always unmarked
    PATIENT_NOUN_MARKED: str = ""      # authored prose: agrees with sex
    HONORIFIC: str = ""
    PRONOUN_SUBJ: str = ""
    # NOTE: no PRONOUN_POSS field -- see module docstring. French "son"/"sa"
    # agree with the possessed noun's gender, not the patient's sex, so a
    # single per-case slot would be linguistically wrong. Templates must
    # hardcode "son"/"sa" per specific noun at translation time.
    # --- provenance for per-format recall analysis ---
    fmt: dict = field(default_factory=dict)


def sample_origin(rng, weights=None):
    keys = list(NAMES)
    w = weights or [NAMES[k]["w"] for k in keys]
    return rng.choices(keys, weights=w)[0]


def build_case(i: int, rng: random.Random, fake: Faker,
               origin_weights=None, ref_date: date | None = None,
               noun_noise: float = 0.05, cities=None,
               noise_rate: float = 0.0,
               ambiguous_rate: float = 0.08) -> Case:
    ref = ref_date or date(2026, 5, 28)
    cities = cities or WALLOON_CITIES

    # --- balanced protected attributes ---
    sex = "M" if i % 2 == 0 else "F"                    # exact 50/50 by construction
    lo, hi, _ = rng.choices(AGE_BANDS, weights=[b[2] for b in AGE_BANDS])[0]
    age = rng.randrange(lo, hi + 1)
    origin = sample_origin(rng, origin_weights)

    birth = ref - timedelta(days=age * 365 + rng.randrange(0, 365))
    # Population-weighted city sampling (real Statbel-derived weights),
    # NOT uniform like the Dutch original -- see module docstring.
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
    RELATIONS = [("Mère", "f"), ("Père", "m"), ("Sœur", "f"), ("Frère", "m"),
                 ("Fille", "f"), ("Fils", "m"), ("Tante", "f"), ("Oncle", "m"),
                 ("Grand-mère", "f"), ("Grand-père", "m"), ("Nièce", "f"), ("Neveu", "m")]
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
    # full site-qualified name (which would produce an unrealistically long
    # slug no real institution actually uses).
    org_network = org.split(" - ")[0]
    slug = (unicodedata.normalize("NFKD", org_network.lower())
            .encode("ascii", "ignore").decode()
            .replace(" ", "").replace("-", ""))

    insz_d = make_insz(birth, sex, rng)
    riziv_d = make_riziv(rng)
    iban_d = make_iban_be(rng)
    street = make_street_fr(rng)
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
    f["AGE"] = rng.choices(["de_ans", "ans", "bare"], weights=[.5, .35, .15])[0]
    age_s = {"de_ans": f"de {age} ans", "ans": f"{age} ans", "bare": str(age)}[f["AGE"]]

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
        NAME_DOCTOR=f"dr. {docs[0]}",
        NAME_RESPONSIBLE=responsible,
        NAME_DOCTOR_2=f"dr. {docs[1]}",
        NAME_DOCTOR_3=f"dr. {docs[2]}",
        NAME_DOCTOR_4=f"dr. {docs[3]}",
        NAME_DOCTOR_5=f"dr. {docs[4]}",
        NAME_DOCTOR_SENDER=f"dr. {docs[5]}",
        NAME_RELATIVE=relative,
        RELATIVE_RELATION=relation,
        AGE=age_s,
        AGE_ADJ=f"{age} ans",
        GENDER="homme" if sex == "M" else "femme",
        DATE_ENCOUNTER=enc_s,
        DATE_VALIDATION=val_s,
        DATE_HISTORY=hist_s,
        DOB=dob_s,
        INSZ=insz_s,
        RIZIV=riziv_s,
        IBAN=iban_s,
        CREDITCARDNUMBER=luhn_card(rng),
        STREET=addr_s,
        ZIPCODE=zipc,
        CITY=city,
        TELEFOON=tel_s,
        TELEFOON_MOBILE=mob_s,
        EMAIL=f"{email_local}@{rng.choice(['voo.be','skynet.be','proximus.be','gmail.com'])}",
        URL=url_s,
        ORGANIZATION=org,
        SPECIALTY=specialty,
        DIAGNOSIS=dx,
        # French masculine is the UNMARKED generic, same design as Dutch.
        DX_EPONYM=rng.choice(DISTRACTORS["eponym_disease"]),
        DX_TEST=rng.choice(DISTRACTORS["eponym_test"]),
        DX_ANATOMY=rng.choice(DISTRACTORS["anatomy_latin"]),
        DX_DRUG=rng.choice(DISTRACTORS["drug_brand"]),
        DX_DRUG_2=rng.choice(DISTRACTORS["drug_brand"]),
        DX_HOMOGRAPH=rng.choice(DISTRACTORS["municipality_homograph"]),
        DX_NUMERIC=rng.choice(DISTRACTORS["numeric_lookalike"]),
        DX_ABBREV=rng.choice(DISTRACTORS["abbreviation"]),
        DX_CODESWITCH=rng.choice(DISTRACTORS["code_switch"]),
        noise_ops=noise_log,
        ambiguous_surname=ambiguous,
        PATIENT_NOUN_GENERIC="patient",
        PATIENT_NOUN_MARKED=(("patient" if sex == "M" else "patiente")
                             if rng.random() > noun_noise
                             else ("patiente" if sex == "M" else "patient")),
        HONORIFIC="monsieur" if sex == "M" else "madame",
        PRONOUN_SUBJ="il" if sex == "M" else "elle",
        fmt=f,
    )


# ===========================================================================
# Label schemes -- UNCHANGED from Dutch original. Keys are Case field names
# (language-agnostic), not language content.
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
    from Dutch original -- language-agnostic mechanics."""
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


DEMO_TEMPLATE = """COURRIER

PATIENT : {NAME_PATIENT}          INSZ {INSZ}
RESPONSABLE : {NAME_DOCTOR}   RIZIV {RIZIV}
DATE : {DATE_ENCOUNTER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère,

    Nous avons vu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}), {PATIENT_NOUN_MARKED}
    de {AGE_ADJ}, en consultation de {SPECIALTY} le {DATE_ENCOUNTER}.
    Adresse : {STREET}, {ZIPCODE} {CITY}. Téléphone : {TELEFOON_MOBILE}.

    Antécédents :
    -------------
    {DATE_HISTORY} : {DIAGNOSIS}
    {DX_EPONYM} ! ATCD {DX_ABBREV}.

    Traitement actuel
    ------------------
    - {DX_DRUG}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1x/j, 8h

    Examen clinique :
    ------------------
    {DX_CODESWITCH}
    {DX_ANATOMY} : pas de lésion. {DX_HOMOGRAPH}.
    {DX_TEST}.

    Familial :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : cancer colorectal à 60 ans

    Conclusion :
    ------------
    Diagnostic : {DIAGNOSIS}. {PRONOUN_SUBJ} ne rapporte pas de nouvelle
    plainte ; le traitement est poursuivi. Contrôle programmé.

    Bien confraternellement
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement le {DATE_VALIDATION}
    {ORGANIZATION} | T {TELEFOON} | {EMAIL} | {URL}
"""


# ===========================================================================
# Audit -- UNCHANGED from Dutch original. Statistical mechanism is
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

    print("\nmorphology as a gender signal (ASYMMETRIC by design):")
    fem = df.PATIENT_NOUN_MARKED == "patiente"
    prec_f = (df.loc[fem, "sex"] == "F").mean() if fem.any() else float("nan")
    rec_f = fem[df.sex == "F"].mean()
    masc = df.PATIENT_NOUN_MARKED == "patient"
    prec_m = (df.loc[masc, "sex"] == "M").mean() if masc.any() else float("nan")
    print(f"    'patiente' -> F : precision {prec_f:.2%}, recall {rec_f:.2%}  (usable)")
    print(f"    'patient'  -> M : precision {prec_m:.2%}  "
          f"(unmarked generic; must NOT be used to infer male)")
    print(f"    generic slots always unmarked: "
          f"{(df.PATIENT_NOUN_GENERIC == 'patient').mean():.0%}")

    print("\nhard-negative coverage (must be tagged O, never labelled):")
    for col, key in [("DX_EPONYM", "eponym_disease"), ("DX_TEST", "eponym_test"),
                     ("DX_ANATOMY", "anatomy_latin"), ("DX_DRUG", "drug_brand"),
                     ("DX_HOMOGRAPH", "municipality_homograph"),
                     ("DX_NUMERIC", "numeric_lookalike"),
                     ("DX_CODESWITCH", "code_switch")]:
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
          "(checks the new population-weighted sampling actually works):")
    total_w = sum(c[5] for c in WALLOON_CITIES)
    target = {c[1]: c[5] / total_w for c in WALLOON_CITIES}
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
    ap.add_argument("--out", default="pii_table_fr.csv")
    ap.add_argument("--jsonl", help="also write JSONL")
    ap.add_argument("--label-scheme", choices=["merged", "split", "flat9"], default="merged")
    ap.add_argument("--ambiguous-rate", type=float, default=0.08,
                    help="share of patients whose surname is also an eponym "
                         "test-name (Snellen, Graves...). 0 disables.")
    ap.add_argument("--noise-rate", type=float, default=0.0,
                    help="pre-normalization character corruption rate. "
                         "Use for TESTING the normalizer; keep 0 for training data.")
    ap.add_argument("--wallonia-only", action="store_true",
                    help="drop Brussels-Capital entries")
    ap.add_argument("--noun-noise", type=float, default=0.05,
                    help="author-error rate on the MARKED noun only "
                         "(template slots are always unmarked generic)")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--origin-weights", help="comma list matching "
                    + ",".join(NAMES.keys()))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    Faker.seed(args.seed)
    fake = Faker("fr_BE")

    ow = [float(x) for x in args.origin_weights.split(",")] if args.origin_weights else None
    cities = [c for c in WALLOON_CITIES if c[4] == 'Wallonie'] if args.wallonia_only else WALLOON_CITIES
    cases = [build_case(i, rng, fake, ow, noun_noise=args.noun_noise, cities=cities,
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
