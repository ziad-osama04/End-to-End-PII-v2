# French template translation — safety rules discovered during v3 rework

These rules exist because `{SPECIALTY}` and `{DIAGNOSIS}` are now properly
parametrized slots (v3 recovery), each resolving to one of ~18 / ~38 possible
values with mixed gender and mixed initial-letter (vowel vs consonant). A
template author cannot know at authoring time which value lands in a given
render, so the surrounding prose must be safe for **every** possible value,
not just whichever one happened to appear in the one representative document
the recovery script sampled.

## Rule 1 — never put a gendered/elidable article directly before `{SPECIALTY}`

`SPECIALTIES` includes "ORL" (vowel-initial) alongside consonant-initial
names, and all of them are used inconsistently for gender in casual French.
`la {SPECIALTY}` / `de la {SPECIALTY}` / `le {SPECIALTY}` breaks on ORL
("la ORL" is ungrammatical; needs "l'ORL"). **Fixed already found and
corrected**: `pii_table_fr.py`'s own `DEMO_TEMPLATE` had this exact bug
("en consultation de {SPECIALTY}") — changed to "en consultation en
{SPECIALTY}".

- Safe: `en {SPECIALTY}` (consultation/follow-up/referral contexts — real
  Belgian clinical-note convention, e.g. "avis en ORL", "suivi en
  Cardiologie")
- Safe: bare `{SPECIALTY}` with no preposition (department/signature labels,
  telegraphic referral shorthand: "réf. {SPECIALTY}")
- Unsafe: `de {SPECIALTY}`, `la {SPECIALTY}`, `du {SPECIALTY}`, `le {SPECIALTY}`

## Rule 2 — never put a gendered adjective/article directly against `{DIAGNOSIS}`

`DIAGNOSES` mixes grammatical genders ("le diabète", "l'asthme", "le
psoriasis" vs. "la fissure anale", "l'anémie ferriprive", "la gonarthrose")
and mixes vowel/consonant-initial values. Any fixed article or
agreement-requiring adjective glued to the slot breaks on roughly half the
pool.

- Safe: `avec {DIAGNOSIS}` (avec never elides, never agrees)
- Safe: colon/label style — `Diagnostic : {DIAGNOSIS}`, `Antécédents :
  {DIAGNOSIS}` (already the convention used in `DEMO_TEMPLATE`)
- Safe: invariant-form adjectives only if truly invariant in BOTH gender AND
  never requiring elision (e.g. "stable" — same spelling both genders)
- Unsafe: `la {DIAGNOSIS}`, `le {DIAGNOSIS}`, `de {DIAGNOSIS}` (elision:
  breaks on vowel-initial diagnoses like "asthme"/"eczéma"/"endométriose"),
  `{DIAGNOSIS} connue/connu` (gender agreement with the diagnosis noun, not
  the patient)

## Rule 3 (already documented, restated for completeness) — patient-gender agreement

`{PATIENT_NOUN_MARKED}` already resolves "patient"/"patiente" correctly.
Never additionally attach a second gendered adjective/participle to the
patient unless it's grammatically invariant ("stable", "mobile"). Prefer
active voice with the object after the verb ("Nous avons revu {NAME_PATIENT},
{PATIENT_NOUN_MARKED} de {AGE_ADJ}, ...") over passive constructions that
force a gendered past participle ("a été vu(e)").

## Rule 4 — never hardcode an honorific ("de heer"/"monsieur") before `{NAME_RELATIVE}`

Found in the Dutch original itself (template `1a45c72c46030984` and others):
a hardcoded "de heer {NAME_RELATIVE}" sits in the SAME template as a later,
properly-slotted `({RELATIVE_RELATION}: {NAME_RELATIVE})` referring to the
same sampled relative. `RELATIVE_RELATION` resolves independently to
Mère/Père/Sœur/Frère/Tante/Oncle/etc. — a hardcoded masculine honorific
directly contradicts a feminine relation about a third of the time. There is
no `{RELATIVE_HONORIFIC}` slot to fix this properly, so the safe fix is to
**drop the honorific before `{NAME_RELATIVE}` entirely** ("chez
{NAME_RELATIVE}" instead of "chez monsieur {NAME_RELATIVE}") rather than
reproduce a latent contradiction. This is an improvement over the Dutch
source, not a faithfulness loss.

## Rule 5 — bare "patiënt(e)"/"patiente" narrative mentions also need slotting

The automated risky-word scan only flags HONORIFIC ("de heer"/"mevrouw") and
PRONOUN_SUBJ ("hij"/"zij") patterns. It does NOT flag plain Dutch
"patiënt"/"patiënte" used as a bare narrative sentence-subject (e.g.
"patiente rapporteert vermoeidheid..."). These must still be manually
caught during translation and rendered as `{PATIENT_NOUN_MARKED}` (or
`{PATIENT_NOUN_GENERIC}` in already-invariant-masculine contexts), not
translated as literal fixed French text — otherwise the same
frozen-narrative problem v3 was built to fix reappears by hand.

## Applies to every template going forward

Every template recovered via v3 now carries real `{SPECIALTY}` and
`{DIAGNOSIS}` slots that v1 had frozen as literal text — so this check must
be (re-)applied to all 50, including the 10 already translated under v1.
