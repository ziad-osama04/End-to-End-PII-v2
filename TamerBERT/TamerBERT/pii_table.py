#!/usr/bin/env python3
"""
pii_table.py -- generate a balanced synthetic PII value table for Flemish
clinical-report templates.

Each row is one complete, internally consistent synthetic "case". Templates
carry placeholders named after the columns ({NAME_PATIENT}, {INSZ}, {CITY} ...)
and are filled by sampling a row.

Design decisions worth knowing before you use it
------------------------------------------------
1. ONE `NAME` label, plus a separate `subject` role.
   The table emits NAME_PATIENT / NAME_DOCTOR / NAME_RELATIVE as separate
   COLUMNS so your template can place them correctly, but every one of them
   carries `label="NAME"` in the emitted annotation. Rationale below in
   `--help-labels`. The `--label-scheme split` flag emits role-specific labels
   instead so you can measure which actually scores better.

2. Internal consistency is enforced.
   birth_date -> age -> INSZ (real mod-97 checksum, parity matches sex)
   city <-> zipcode <-> province   (never mismatched)
   sex <-> gendered Dutch nouns    (patient / patiente)
   sex-specific diagnoses only assigned to the compatible sex

3. Format variety is sampled, not fixed.
   Every value is rendered through one of several real Belgian surface forms,
   and the chosen variant is recorded in `*_fmt`. Train on variety; report
   per-format recall afterwards.

4. Fairness stratification is explicit.
   sex, age band, name origin, province, and urbanicity are sampled to target
   distributions and are NOT correlated with diagnosis (except where clinically
   required). `--audit` prints the realised distributions and independence
   checks.

   `name_origin` exists to measure DIFFERENTIAL RECALL: a model trained only on
   Flemish names under-detects Maghrebi, Turkish, Slavic and Central African
   names, which means weaker privacy protection for those patients. That is the
   concrete fairness failure this generator is built to expose. It is a
   generation-time stratification variable for evaluation slicing only. It is
   not a model output and must not be stored as an attribute of any person.

Usage
    python3 pii_table.py -n 2000 --out pii_table.csv --audit
    python3 pii_table.py -n 500 --label-scheme split --out split.csv
    python3 pii_table.py --demo            # show one filled template
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
# Reference data: Belgium / Flanders
# ===========================================================================

# (zipcode, city, province, urbanicity, region). Zip and city always travel
# together. Brussels-Capital is NOT Flanders; it is included at a small share
# because Flemish hospitals do treat Brussels residents. Use --flanders-only to
# drop it.
CITIES = [
    # (zipcode, city, province, urbanicity, region)
    # Brussels-Capital is NOT Flanders. Included at a small share because
    # Flemish hospitals do treat Brussels residents. Drop with --flanders-only.
    ("1000", "Brussel",              "Brussel-Hoofdstad", "urban", "Brussel"),
    ("1030", "Schaarbeek",           "Brussel-Hoofdstad", "urban", "Brussel"),
    ("1500", "Halle",                "Vlaams-Brabant",  "town",  "Vlaanderen"),
    ("1700", "Dilbeek",              "Vlaams-Brabant",  "town",  "Vlaanderen"),
    ("1800", "Vilvoorde",            "Vlaams-Brabant",  "town",  "Vlaanderen"),
    ("1930", "Zaventem",             "Vlaams-Brabant",  "town",  "Vlaanderen"),
    ("2000", "Antwerpen",            "Antwerpen",       "urban", "Vlaanderen"),
    ("2018", "Antwerpen",            "Antwerpen",       "urban", "Vlaanderen"),
    ("2200", "Herentals",            "Antwerpen",       "town",  "Vlaanderen"),
    ("2300", "Turnhout",             "Antwerpen",       "town",  "Vlaanderen"),
    ("2400", "Mol",                  "Antwerpen",       "rural", "Vlaanderen"),
    ("2440", "Geel",                 "Antwerpen",       "town",  "Vlaanderen"),
    ("2500", "Lier",                 "Antwerpen",       "town",  "Vlaanderen"),
    ("2800", "Mechelen",             "Antwerpen",       "urban", "Vlaanderen"),
    ("2860", "Sint-Katelijne-Waver", "Antwerpen",       "rural", "Vlaanderen"),
    ("3000", "Leuven",               "Vlaams-Brabant",  "urban", "Vlaanderen"),
    ("3200", "Aarschot",             "Vlaams-Brabant",  "rural", "Vlaanderen"),
    ("3500", "Hasselt",              "Limburg",         "urban", "Vlaanderen"),
    ("3600", "Genk",                 "Limburg",         "town",  "Vlaanderen"),
    ("3630", "Maasmechelen",         "Limburg",         "rural", "Vlaanderen"),
    ("3700", "Tongeren",             "Limburg",         "rural", "Vlaanderen"),
    ("3800", "Sint-Truiden",         "Limburg",         "town",  "Vlaanderen"),
    ("3900", "Pelt",                 "Limburg",         "rural", "Vlaanderen"),
    ("8000", "Brugge",               "West-Vlaanderen", "urban", "Vlaanderen"),
    ("8300", "Knokke-Heist",         "West-Vlaanderen", "town",  "Vlaanderen"),
    ("8400", "Oostende",             "West-Vlaanderen", "town",  "Vlaanderen"),
    ("8500", "Kortrijk",             "West-Vlaanderen", "urban", "Vlaanderen"),
    ("8600", "Diksmuide",            "West-Vlaanderen", "rural", "Vlaanderen"),
    ("8700", "Tielt",                "West-Vlaanderen", "rural", "Vlaanderen"),
    ("8800", "Roeselare",            "West-Vlaanderen", "town",  "Vlaanderen"),
    ("8900", "Ieper",                "West-Vlaanderen", "town",  "Vlaanderen"),
    ("9000", "Gent",                 "Oost-Vlaanderen", "urban", "Vlaanderen"),
    ("9100", "Sint-Niklaas",         "Oost-Vlaanderen", "town",  "Vlaanderen"),
    ("9200", "Dendermonde",          "Oost-Vlaanderen", "town",  "Vlaanderen"),
    ("9300", "Aalst",                "Oost-Vlaanderen", "town",  "Vlaanderen"),
    ("9400", "Ninove",               "Oost-Vlaanderen", "rural", "Vlaanderen"),
    ("9500", "Geraardsbergen",       "Oost-Vlaanderen", "rural", "Vlaanderen"),
    ("9600", "Ronse",                "Oost-Vlaanderen", "rural", "Vlaanderen"),
    ("9700", "Oudenaarde",           "Oost-Vlaanderen", "town",  "Vlaanderen"),
]

STREET_STEM = [
    "Kerk", "Dorp", "Molen", "Nieuw", "Oude", "Hoge", "Lange", "Korte", "Groene",
    "Stations", "School", "Veld", "Berg", "Beek", "Linde", "Eiken", "Wilgen",
    "Bloem", "Zonne", "Vijver", "Kasteel", "Abdij", "Markt", "Vissers", "Smid",
    "Brouwers", "Wever", "Bakker", "Hoeve", "Kouter", "Meers", "Gaver",
]
STREET_SUFFIX = [
    "straat", "laan", "steenweg", "dreef", "weg", "plein", "kaai", "baan",
    "pad", "lei", "vest", "wal", "berg", "hof", "dries", "park", "ring",
]

# Name pools stratified by origin. Weights approximate the Flemish patient
# population, which is NOT majority-only. Adjust with --origin-weights.
NAMES = {
    "flemish": {
        "w": 0.62,
        "m": ["Jan", "Marc", "Luc", "Dirk", "Wim", "Bart", "Kris", "Tom", "Stijn",
              "Jonas", "Wouter", "Filip", "Geert", "Koen", "Pieter", "Lode", "Rik"],
        "f": ["An", "Els", "Katrien", "Griet", "Lieve", "Ann", "Sofie", "Leen",
              "Marleen", "Hilde", "Veerle", "Inge", "Nele", "Tine", "Femke", "Lore"],
        "s": ["Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Willems",
              "Claes", "Goossens", "Wouters", "De Smet", "Dubois", "Lambert",
              "Van den Berghe", "Vermeulen", "De Clercq", "Van Damme",
              "Verhoeven", "De Backer", "Coppens", "Van Acker", "Declercq"],
    },
    "maghrebi": {
        "w": 0.12,
        "m": ["Mohamed", "Youssef", "Karim", "Bilal", "Rachid", "Hamza", "Anas",
              "Ismail", "Adil", "Nabil", "Yassine", "Mehdi"],
        "f": ["Fatima", "Amina", "Khadija", "Nadia", "Samira", "Sara", "Leila",
              "Yasmine", "Meryem", "Hafida", "Ilham"],
        "s": ["El Amrani", "Benali", "Ouazzani", "Cherkaoui", "El Habti",
              "Bouzid", "Rahmani", "Idrissi", "El Fassi", "Bennani", "Alaoui"],
    },
    "turkish": {
        "w": 0.06,
        "m": ["Mehmet", "Emre", "Serkan", "Kaan", "Burak", "Onur", "Cem", "Tolga"],
        "f": ["Ayse", "Elif", "Zeynep", "Merve", "Esra", "Gul", "Deniz", "Selin"],
        "s": ["Yilmaz", "Demir", "Kaya", "Sahin", "Celik", "Ozturk", "Arslan",
              "Dogan", "Aydin", "Korkmaz"],
    },
    "central_african": {
        "w": 0.05,
        "m": ["Patrick", "Christian", "Emmanuel", "Joseph", "Didier", "Gaston",
              "Serge", "Blaise"],
        "f": ["Grace", "Esther", "Nadine", "Chantal", "Mireille", "Sylvie",
              "Bernadette", "Josiane"],
        "s": ["Mbala", "Kabongo", "Ilunga", "Nkosi", "Mukendi", "Tshibangu",
              "Lumumba", "Kalala", "Mwamba", "Bope"],
    },
    "southern_european": {
        "w": 0.08,
        "m": ["Marco", "Giuseppe", "Antonio", "Salvatore", "Paulo", "Rafael",
              "Miguel", "Angelo"],
        "f": ["Maria", "Giulia", "Rosa", "Carmela", "Ana", "Sofia", "Elena",
              "Lucia"],
        "s": ["Rossi", "Esposito", "Ferrari", "Romano", "Silva", "Santos",
              "Garcia", "Fernandez", "Costa", "Moreira"],
    },
    "eastern_european": {
        "w": 0.07,
        "m": ["Piotr", "Andrzej", "Tomasz", "Ionut", "Vasile", "Dimitar",
              "Miroslav", "Krzysztof"],
        "f": ["Agnieszka", "Katarzyna", "Magdalena", "Ioana", "Elena",
              "Svetlana", "Zuzana", "Iwona"],
        "s": ["Kowalski", "Nowak", "Wisniewski", "Popescu", "Ionescu",
              "Dimitrov", "Novak", "Zielinski", "Kaminski", "Marinescu"],
    },
}

SPECIALTIES = [
    "Gastro-enterologie", "Fysische Geneeskunde en revalidatie", "Oftalmologie",
    "Pneumologie", "Cardiologie", "Neurologie", "Dermatologie", "Endocrinologie",
    "Nefrologie", "Orthopedie", "Urologie", "Gynaecologie", "Reumatologie",
    "Oncologie", "NKO", "Geriatrie", "Vaatheelkunde", "Algemene Heelkunde",
]

# (diagnosis, specialty, sex_restriction) -- sex_restriction None = either.
# Entries marked (pdf) came from the five real seed letters.
DIAGNOSES = [
    ("anale fissuur",                          "Gastro-enterologie", None),   # pdf
    ("lichte chronische niet specifieke colitis","Gastro-enterologie", None),  # pdf
    ("ulcus anastomoticum",                    "Gastro-enterologie", None),   # pdf
    ("ferriprieve anaemie",                    "Gastro-enterologie", None),   # pdf
    ("status na gastric bypass (RYGB)",        "Gastro-enterologie", None),   # pdf
    ("refluxoesofagitis graad B",              "Gastro-enterologie", None),
    ("diverticulose sigmoid",                  "Gastro-enterologie", None),
    ("coeliakie",                              "Gastro-enterologie", None),
    ("epididymitis links",                     "Urologie",           "M"),    # pdf
    ("supraspinatuspeestendinose bilateraal",  "Fysische Geneeskunde en revalidatie", None),  # pdf
    ("subacromiale bursitis",                  "Fysische Geneeskunde en revalidatie", None),  # pdf
    ("bekkenbodemhypertonie",                  "Fysische Geneeskunde en revalidatie", None),  # pdf
    ("laterale epicondylitis rechts",          "Fysische Geneeskunde en revalidatie", None),
    ("lumbaal facettair syndroom",             "Fysische Geneeskunde en revalidatie", None),
    ("geen diabetische retinopathie",          "Oftalmologie",       None),   # pdf
    ("cataract incipiens bilateraal",          "Oftalmologie",       None),
    ("open kamerhoek glaucoom",                "Oftalmologie",       None),
    ("droge maculadegeneratie",                "Oftalmologie",       None),
    ("obstructief longlijden GOLD II",         "Pneumologie",        None),
    ("astma, goed gecontroleerd",              "Pneumologie",        None),
    ("obstructief slaapapneusyndroom",         "Pneumologie",        None),
    ("ziekte van Von Willebrand",              "Algemene Heelkunde", None),   # pdf
    ("epilepsie, in remissie",                 "Neurologie",         None),   # pdf
    ("migraine met aura",                      "Neurologie",         None),
    ("perifere polyneuropathie",               "Neurologie",         None),
    ("type 2 diabetes mellitus",               "Endocrinologie",     None),   # pdf (co diabetes)
    ("hypothyreoidie",                         "Endocrinologie",     None),
    ("osteoporose",                            "Reumatologie",       None),
    ("reumatoide artritis",                    "Reumatologie",       None),
    ("boezemfibrilleren",                      "Cardiologie",        None),
    ("arteriele hypertensie",                  "Cardiologie",        None),
    ("chronische nierinsufficientie stadium 3","Nefrologie",         None),
    ("gonartrose bilateraal",                  "Orthopedie",         None),
    ("carpaal tunnelsyndroom",                 "Orthopedie",         None),
    ("benigne prostaathyperplasie",            "Urologie",           "M"),
    ("endometriose",                           "Gynaecologie",       "F"),
    ("myomateuze uterus",                      "Gynaecologie",       "F"),
    ("atopisch eczeem",                        "Dermatologie",       None),
    ("psoriasis vulgaris",                     "Dermatologie",       None),
    ("chronische rhinosinusitis",              "NKO",                None),
]

HOSPITAL_PREFIX = ["AZ", "UZ", "Ziekenhuis", "Kliniek", "Algemeen Ziekenhuis"]
HOSPITAL_STANDALONE = ["ZNA Middelheim", "AZ Klina", "AZ Delta", "AZ Turnhout",
                       "Jessa Ziekenhuis", "Imeldaziekenhuis", "AZ Alma"]
HOSPITAL_STEM = [
    "Sint-Lucas", "Sint-Vincentius", "Sint-Jozef", "Sint-Rembert", "Sint-Blasius",
    "Onze-Lieve-Vrouw", "Heilig Hart", "Maria Middelares", "De Voorzorg",
    "Groeninge", "Vesalius", "Damiaan", "Nikolaas", "Rivierenland", "Zeepreventorium",
]

AGE_BANDS = [(0, 17, 0.06), (18, 34, 0.16), (35, 49, 0.19),
             (50, 64, 0.24), (65, 79, 0.24), (80, 95, 0.11)]


# ===========================================================================
# HARD NEGATIVES
# These are strings that LOOK like PII and must be tagged O. They are emitted
# into the document text but deliberately NOT registered in any label scheme,
# so render() leaves them unlabelled. Without them the model never learns to
# reject them, which is how the incumbent masker produced "p[ADRES]nd" by
# matching the municipality Asse inside the word "passend".
# ===========================================================================

DISTRACTORS = {
    # Person names inside disease names. Dutch construction is the giveaway.
    "eponym_disease": [
        "ziekte van Von Willebrand", "ziekte van Crohn", "ziekte van Parkinson",
        "syndroom van Sjogren", "syndroom van Raynaud", "ziekte van Graves",
        "ziekte van Bechterew", "syndroom van Guillain-Barre",
        "teken van Lasegue", "manoeuvre van Valsalva", "ziekte van Hashimoto",
        "syndroom van Cushing", "ziekte van Dupuytren",
    ],
    # Bare eponyms with NO "van" construction -> gazetteer territory.
    "eponym_test": [
        "Snellen 1", "Humphrey - perimetrie", "Jaeger transfertest",
        "Goldmann applanatie", "Schirmer-test", "teken van Tinel",
        "Phalen-test", "Romberg negatief", "Glasgow Coma Scale 15",
        "Barthel-index 90", "Bristol-schaal type 4",
    ],
    # Latin anatomy abbreviated as initial + capitalised word.
    "anatomy_latin": [
        "M. Biceps caput longum", "m. Infraspinatus", "M. Subscapularis",
        "M. Supraspinatus", "m. Deltoideus", "N. Medianus", "A. Radialis",
        "lig. Collaterale mediale", "V. Saphena magna",
    ],
    # Drug brand names: look like ORG or PERSON.
    "drug_brand": [
        "Asaflow 80 mg", "Atorstatine 20 mg", "D-cure 25 000 ie",
        "Glucagen hypokit", "Lyumjev kwikpen", "Toujeo solostar",
        "Lambipol 100 mg", "L-thyroxine 50 mcg", "Metformine viatris 500 mg",
        "Nexiam 20 mg", "Ozempic 1 mg", "Progor retard 180 mg",
        "Sipralexa 20 mg", "Depakine chrono 500 mg", "Pantomed 40 mg",
        "Injectafer 1000 mg", "Ventolin aerosol", "Diltiazemzalf 2%",
        "Cose protect", "Trianal suppo", "Ibuprofen 400 mg", "Paracetamol 1 g",
    ],
    # Flemish municipality names embedded in ordinary Dutch words. This is the
    # exact class that broke the incumbent tool.
    "municipality_homograph": [
        "beeld passend bij bursitis",              # Asse
        "geel verkleurde sclerae",                 # Geel
        "peervormige galblaas",                    # Peer
        "boomstructuur van de bronchi",            # Boom
        "hamstringletsel links",                   # Ham
        "molaire zwangerschap uitgesloten",        # Mol
        "as 165 graden",                           # As
        "lintvormige stoelgang",                   # Lint
        "beers-teken afwezig",                     # Beers
    ],
    # Numeric strings that bait identifier regexes.
    "numeric_lookalike": [
        "1/d", "2/d", "1/w", "3x/week", "1 a 2 /d", "8u", "12u", "18u", "22u",
        "BD: 146/68", "HR: 68", "spO2: 94%", "2cc", "3x", "25 000 ie",
        "100 e/ml 3 ml", "300 ie/ml 1.5 ml", "0.5 mg", "4.95*",
        "-0.25 ^ -0.25 as 165 graden", "FEV1/FVC 73.17", "BMI 20.808",
        "T 37.2", "pH 7.38",
    ],
    # Clinical abbreviations that resemble initials or IDs.
    "abbreviation": [
        "RYGB", "PRP", "SSp", "ESWT", "PPI", "NSAID", "APO", "PTO", "ODS",
        "OD", "OS", "i.o.m.", "antec.", "ivm", "tvv", "nle", "co", "z.n.",
    ],
    # Surnames that are ALSO eponyms/homographs. These are injected into the
    # person-name pool at a low rate so the same token appears BOTH labelled
    # (as a real NAME) and unlabelled (inside an eponym). That forces the model
    # to discriminate on CONTEXT rather than memorising "Snellen -> always O".
    # Without this, a patient genuinely named Snellen is silently missed.
    "_ambiguous_surnames": [
        "Snellen", "Jaeger", "Graves", "Romberg", "Phalen", "Goldmann",
        "Schirmer", "Tinel", "Bristol", "Barthel", "Peer", "Mol", "Boom",
        "Lint", "Beers", "Van Peer", "De Boom", "Van Mol",
    ],
    # English inside Dutch prose: code-switching stress for the tokenizer.
    "code_switch": [
        "Painful arc beiderzijds +", "blurr-test", "SSp testen positief",
        "full range of motion", "no evidence of malignancy",
        "watchful waiting", "shared decision making",
    ],
}


# ---------------------------------------------------------------------------
# Character-level noise: simulates PRE-normalization text.
# Use this to TEST the normalizer, not to train the model. In production the
# model receives post-normalization text, so training on noisy text would
# teach it to handle corruption the pipeline is supposed to remove.
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
# Belgian identifier construction (real checksums)
# ===========================================================================

def make_insz(birth: date, sex: str, rng: random.Random) -> str:
    """11 digits: YYMMDD + SSS (odd=M, even=F) + CC (mod-97 check).

    NOTE: parity encodes sex. This is a genuine leak channel; keep it
    consistent with `sex` so the corpus is realistic, then TEST whether your
    model's gender predictions correlate with it.
    """
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
    rearr = body + "1114" + "00"          # BE -> 11 14, placeholder check 00
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
# Surface-format variants (sampled, and recorded)
# ===========================================================================

def fmt_insz(d: str, rng) -> tuple[str, str]:
    # OBSERVED: "INSZ12051560042" -- plain 11 digits, no separators, and glued
    # straight onto the label. Weight "plain" heavily; the dotted form is the
    # documented convention but is NOT what this hospital emits.
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
    """Returns (surface, variant, kind). kind = landline | mobile | service.

    "service" (070/078 premium-rate, 0800/0900 toll-free/premium) exercises
    the BELGIUM_PHONE_REGEX branches that landline/mobile numbers never hit,
    so training data actually contains examples for that branch."""
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
    MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
              "augustus", "september", "oktober", "november", "december"]
    yy = d.year % 100
    # Full day+month+year forms -- always safe for DOB (allow_partial=False)
    # too, since they never lose precision.
    opts = ["dd/mm/yyyy", "dd-mm-yyyy", "dd.mm.yyyy", "d/m/yyyy",
            "yyyy-mm-dd", "text_nl", "text_abbr",
            "dd/mm/yy", "dd-mm-yy", "dd.mm.yy"]
    wts = [0.28, 0.25, 0.06, 0.07, 0.08, 0.09, 0.09, 0.04, 0.02, 0.02]
    if allow_partial:
        # No-year / compact / year-first forms -- real in encounter dates
        # ("op 24/04 werd...") but never a real DOB, hence gated here.
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
        "text_nl":    f"{d.day} {MONTHS[d.month-1]} {d.year}",
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
    """The Belgian birth marker. Deliberately varies the ring codepoint so your
    confusable-folding step is exercised by the training data. Occasionally
    uses the Dutch text-month form ("degree D maand YYYY") instead of a
    numeric date, matching patterns.py's DOB text-month branch."""
    ring = rng.choices(["\u00B0", "\u00BA"], weights=[0.75, 0.25])[0]
    if rng.random() < 0.15:
        MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
                  "augustus", "september", "oktober", "november", "december"]
        body, v = f"{d.day} {MONTHS[d.month - 1]} {d.year}", "text_nl"
    else:
        body, v = fmt_date(d, rng, allow_partial=False)
    kind = "degree" if ring == "\u00B0" else "masc_ordinal"
    return f"{ring}{body}", f"{kind}_{v}"


def fmt_address(street: str, nr: str, rng) -> tuple[str, str]:
    v = rng.choices(
        ["plain", "bus", "slash", "letter", "floor", "postbus"],
        weights=[0.50, 0.18, 0.09, 0.09, 0.08, 0.06])[0]
    if v == "plain":  return f"{street} {nr}", v
    if v == "bus":    return f"{street} {nr} bus {rng.randrange(1, 20)}", v
    if v == "slash":  return f"{street} {nr}/{rng.randrange(1, 20)}", v
    if v == "letter": return f"{street} {nr}{rng.choice('ABC')}", v
    if v == "floor":
        floor = rng.choice(["gelijkvloers", "1ste", "2de", "3de", "4de"])
        return f"{street} {nr}, {floor} verdieping", v
    return f"Postbus {rng.randrange(1, 999)}", v


def fmt_url(slug: str, rng: random.Random) -> tuple[str, str]:
    """Belgian hospital URL, matching every branch of patterns.py's
    P["URL"] (scheme+www, scheme-only, www-only, bare domain, with/without
    a path or query string)."""
    tld = rng.choices(["be", "com"], weights=[0.9, 0.1])[0]
    path = rng.choice(["", "", "/patientenportaal", "/contact",
                       f"/afspraak?id={rng.randrange(1000, 9999)}"])
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
    PRONOUN_POSS: str = ""
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
    cities = cities or CITIES

    # --- balanced protected attributes ---
    sex = "M" if i % 2 == 0 else "F"                    # exact 50/50 by construction
    lo, hi, _ = rng.choices(AGE_BANDS, weights=[b[2] for b in AGE_BANDS])[0]
    age = rng.randrange(lo, hi + 1)
    origin = sample_origin(rng, origin_weights)

    birth = ref - timedelta(days=age * 365 + rng.randrange(0, 365))
    zipc, city, province, urban, region = rng.choice(cities)

    pool = NAMES[origin]
    given = rng.choice(pool["m" if sex == "M" else "f"])
    # A small share of surnames are drawn from the ambiguous pool, so the same
    # string occurs both as a labelled NAME here and unlabelled inside an
    # eponym elsewhere in the corpus. Context becomes the only discriminator.
    if rng.random() < ambiguous_rate:
        surname = rng.choice(DISTRACTORS["_ambiguous_surnames"])
        ambiguous = True
    else:
        surname = rng.choice(pool["s"])
        ambiguous = False
    patient = f"{given} {surname}"

    # Doctors are sampled from the SAME origin distribution, independently of
    # the patient. Correlating them would inject a spurious association.
    doc_origin = sample_origin(rng, origin_weights)
    # OBSERVED IN THE REAL LETTERS: signature-block physicians appear as
    # "dr. Surname" with NO given name (dr. Van Laere, dr. Adriaenssens,
    # dr. De Bruycker). Only the VERANTWOORDELIJKE header field carries a
    # full "Given Surname". Generating full names everywhere taught the model
    # the wrong span shape.
    docs = []
    for _ in range(6):
        o = NAMES[doc_origin]
        docs.append(rng.choice(o["s"]))          # surname only
        doc_origin = sample_origin(rng, origin_weights)
    # the responsible physician in the header IS a full name
    ro = NAMES[sample_origin(rng, origin_weights)]
    responsible = f"{rng.choice(ro[rng.choice(['m','f'])])} {rng.choice(ro['s'])}"

    # Relatives share ancestry with the patient, and their given name must
    # agree with the relation word ("Moeder (Kaan ...)" is a data bug).
    rp = NAMES[origin]
    RELATIONS = [("Moeder", "f"), ("Vader", "m"), ("Zus", "f"), ("Broer", "m"),
                 ("Dochter", "f"), ("Zoon", "m"), ("Tante", "f"), ("Oom", "m"),
                 ("Grootmoeder", "f"), ("Grootvader", "m"), ("Nicht", "f"), ("Neef", "m")]
    relation, rel_sex = rng.choice(RELATIONS)
    relative = f"{rng.choice(rp[rel_sex])} {rng.choice(rp['s'])}"

    # --- diagnosis: sex-compatible only, otherwise independent of everything ---
    pool_dx = [d for d in DIAGNOSES if d[2] is None or d[2] == sex]
    dx, specialty, _ = rng.choice(pool_dx)

    # --- dates ---
    enc = ref - timedelta(days=rng.randrange(0, 45))
    val = enc + timedelta(days=rng.randrange(0, 3))
    hist = enc - timedelta(days=rng.randrange(200, 4000))

    org = (rng.choice(HOSPITAL_STANDALONE) if rng.random() < 0.25
           else f"{rng.choice(HOSPITAL_PREFIX)} {rng.choice(HOSPITAL_STEM)}")
    slug = (unicodedata.normalize("NFKD", org.lower())
            .encode("ascii", "ignore").decode()
            .replace(" ", "").replace("-", ""))

    insz_d = make_insz(birth, sex, rng)
    riziv_d = make_riziv(rng)
    iban_d = make_iban_be(rng)
    street = f"{rng.choice(STREET_STEM)}{rng.choice(STREET_SUFFIX)}"
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
    f["AGE"] = rng.choices(["jarige", "jaar", "bare"], weights=[.5, .35, .15])[0]
    age_s = {"jarige": f"{age}-jarige", "jaar": f"{age} jaar", "bare": str(age)}[f["AGE"]]

    email_local = (unicodedata.normalize("NFKD", f"{given}.{surname}".lower())
                   .encode("ascii", "ignore").decode().replace(" ", ""))

    # Optional pre-normalization corruption, applied to PII surfaces only.
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
        AGE_ADJ=f"{age}-jarige",
        GENDER="man" if sex == "M" else "vrouw",
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
        EMAIL=f"{email_local}@{rng.choice(['telenet.be','skynet.be','proximus.be','gmail.com'])}",
        URL=url_s,
        ORGANIZATION=org,
        SPECIALTY=specialty,
        DIAGNOSIS=dx,
        # Dutch masculine is the UNMARKED generic. Template slots therefore use
        # "patient" regardless of sex; only authored prose marks the feminine.
        # `noun_noise` is now a genuine author-error rate, not a coin flip.
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
        HONORIFIC="de heer" if sex == "M" else "mevrouw",
        PRONOUN_SUBJ="hij" if sex == "M" else "zij",
        PRONOUN_POSS="zijn" if sex == "M" else "haar",
        fmt=f,
    )


# ===========================================================================
# Label schemes
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
# The exact 9-label spec: NAME (patient/doctor/relative/organisation all
# merged -- an org/hospital name is PII the same way a person's is), AGE,
# DATE, INSZ, RIZIV, ADDRESS (STREET+ZIPCODE+CITY merged into one entity
# type), PHONE, URL. GENDER is deliberately left mapped but never actually
# emits a span: no template places a bare {GENDER} placeholder, so the key
# only matters if a future template adds one -- see the DERIVED note in
# patterns.py's module docstring. GENDER itself stays available as a Case/
# CSV column for retrieval, exactly as requested, just never as trained text.
FLAT9 = dict(MERGED, **{
    "NAME_RESPONSIBLE": "NAME",   # was unmapped under MERGED -- real gap, fixed
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
    """Fill {PLACEHOLDER} slots and return (text, annotations).

    Annotations are char spans with label + subject + format variant, ready to
    feed the BIO aligner.
    """
    d = asdict(case)
    out, spans, i = [], [], 0
    pos = 0
    import re as _re
    # {SLOT} or {SLOT:width} -- width left-justifies the value with trailing
    # spaces so fixed-column headers stay aligned AFTER filling. The span
    # covers the value only; the padding is outside it.
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


DEMO_TEMPLATE = """BRIEF

PATIENT: {NAME_PATIENT}          INSZ {INSZ}
VERANTWOORDELIJKE: {NAME_DOCTOR}   RIZIV {RIZIV}
DATUM: {DATE_ENCOUNTER}

Inhoud van het verslag
    {ORGANIZATION}
    {SPECIALTY}

    Geachte Collega,

    Wij zagen uw {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) op de raadpleging
    {SPECIALTY} op {DATE_ENCOUNTER}. De {AGE} {PATIENT_NOUN_MARKED} woont te
    {STREET}, {ZIPCODE} {CITY}, bereikbaar op {TELEFOON_MOBILE}.

    Voorgeschiedenis:
    -----------------
    {DATE_HISTORY}: {DIAGNOSIS}
    {DX_EPONYM} ! Antec. {DX_ABBREV}.

    Huidige medicatie
    -----------------
    - {DX_DRUG}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1/d, 8u

    Klinisch onderzoek:
    -------------------
    {DX_CODESWITCH}
    {DX_ANATOMY}: geen letsel. {DX_HOMOGRAPH}.
    {DX_TEST}.

    Familiaal:
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}): darmkanker op 60-jarige leeftijd

    Besluit:
    --------
    Diagnose: {DIAGNOSIS}. {PRONOUN_SUBJ} meldt geen nieuwe klachten;
    {PRONOUN_POSS} behandeling wordt verdergezet. Controle gepland.

    Met collegiale hoogachting
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Dit verslag werd elektronisch gevalideerd op {DATE_VALIDATION}
    {ORGANIZATION} | T {TELEFOON} | {EMAIL} | {URL}
"""


# ===========================================================================
# Audit
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
    # A FIXED deviation threshold is wrong here: the sampling error on each
    # diagnosis depends on how many rows it got. Score in standard errors and
    # compare against the max |z| expected across k independent tests.
    import math
    sexed = {d[0] for d in DIAGNOSES if d[2]}
    sub = df[~df.DIAGNOSIS.isin(sexed)]
    ct = pd.crosstab(sub.DIAGNOSIS, sub.sex)
    ct["n"] = ct.sum(axis=1)
    ct["p_M"] = ct["M"] / ct["n"]
    ct["se"] = (0.25 / ct["n"]) ** 0.5
    ct["z"] = (ct["p_M"] - 0.5) / ct["se"]
    k = len(ct)
    # Expected max |z| over k standard normals, Bonferroni-style critical value.
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


# ===========================================================================
# CLI
# ===========================================================================

def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="pii_table.csv")
    ap.add_argument("--jsonl", help="also write JSONL")
    ap.add_argument("--label-scheme", choices=["merged", "split", "flat9"], default="merged")
    ap.add_argument("--ambiguous-rate", type=float, default=0.08,
                    help="share of patients whose surname is also an eponym "
                         "or municipality (Snellen, Graves, Mol, Peer...). "
                         "Forces context-based discrimination. 0 disables.")
    ap.add_argument("--noise-rate", type=float, default=0.0,
                    help="pre-normalization character corruption rate "
                         "(NBSP, soft hyphen, NFD, en-dash...). Use for "
                         "TESTING the normalizer; keep 0 for training data.")
    ap.add_argument("--flanders-only", action="store_true",
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
    fake = Faker("nl_BE")

    ow = [float(x) for x in args.origin_weights.split(",")] if args.origin_weights else None
    cities = [c for c in CITIES if c[4] == 'Vlaanderen'] if args.flanders_only else CITIES
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
