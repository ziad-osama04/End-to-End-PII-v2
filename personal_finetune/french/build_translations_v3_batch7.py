# -*- coding: utf-8 -*-
"""Batch 7: 4 more templates."""
import json

TEMPLATES = [
{
"template_hash": "bfe25d0bb0a5dbc9", "letter_type": "consultatiebrief", "specialty": "Oftalmologie",
"masked_text_fr": """COURRIER

PATIENT :
{NAME_PATIENT}
INSZ{INSZ}

RESPONSABLE :
{NAME_RESPONSIBLE}
RIZIV{RIZIV}

DATE :
{DATE_ENCOUNTER} 02:00
ENVOYÉ PAR :
{NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère

    Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en
    consultation en {SPECIALTY}.

    Motif de consultation :
    ------------
    {DATE_HISTORY} : {DIAGNOSIS} Troubles réfractifs depuis des mois, {DX_ABBREV}
    {DX_EPONYM} ! Co diabète et hypertension

    Antécédents familiaux :
    ---------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_DRUG} nécessaire depuis 50 ans

    Allergies :
    -------
    Pas d'allergie connue

    Traitement à domicile :
    ---------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - {DX_HOMOGRAPH}, {DX_NUMERIC}, 9h
    Aucun traitement à domicile enregistré

    Anamnèse :
    ---------
    {PRONOUN_SUBJ} signale une détérioration progressive de la capacité de lecture ces {DX_NUMERIC} dernières semaines.
    Difficulté de mise au point de près, également pour conduire le soir {DX_ABBREV}
    diffusion lumineuse. Pas de douleur, pas d'œil rouge, pas de {DX_TEST}.
    ATCD {DX_ABBREV}.

    État :
    -------
    {AGE_ADJ} en {DX_CODESWITCH} état général stable.
    Pas de fièvre, pas de perte de poids. Bon état de conscience, bonne coopération.

    Examen clinique :
    -------------------
    ACUITÉ : œil g : 0,8, œil d : 0,9, avec lunettes Œil g : {DX_ANATOMY} intact,
    réaction pupillaire normale Œil d : {DX_ABBREV}, effet secondaire de {DX_DRUG_2} exclu Pas
    d'atrophie du nerf optique, pas de {DX_TEST} !

    Examen technique :
    --------------------
    OCT : {DIAGNOSIS} débutante présente, bilatérale Biométrie :
    longueur œil g : 23,2mm, œil d : 23,0mm Tonométrie : œil g : 18 mmHg, œil d : 17 mmHg
    Champ visuel : champs visuels périphériques {DX_NUMERIC} intacts

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} troubles réfractifs avec
    {DIAGNOSIS} confirmée à l'OCT. Situation oculaire stable. Pas d'indication
    d'intervention. Le régime actuel de {DX_DRUG_2} est poursuivi {DX_ABBREV}
    stabilité {DX_HOMOGRAPH}.

    --> Correction lunettes adaptée, contrôle dans 12 mois.
    --> Conseil de contrôle annuel en {SPECIALTY} {DX_ABBREV}
    {DX_EPONYM}.
    Pas d'orientation vers la chirurgie.

    Examens techniques :
    ------------------------
    OCT rétine {DATE_ENCOUNTER} Réfraction automatique {DATE_ENCOUNTER} Tonométrie de Goldmann
    {DATE_ENCOUNTER}

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}
    {NAME_DOCTOR_4}
    {NAME_DOCTOR_5}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 12:20
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'mevrouw activeerbaar, cooperatief' (gendered adjective 'cooperatief/cooperatieve' trap) -> 'Bon etat de conscience, bonne cooperation' (reuses/extends the established invariant-noun fix).",
    "'haar huidige X regime' (PRONOUN_POSS) -> 'Le regime actuel de X' (dropped possessive).",
]},

{
"template_hash": "c106c5d80b619d6d", "letter_type": "consultatiebrief", "specialty": "Endocrinologie",
"masked_text_fr": """COURRIER

PATIENT :
{NAME_PATIENT}
INSZ{INSZ}

RESPONSABLE :
{NAME_RESPONSIBLE}
RIZIV{RIZIV}

DATE :
{DATE_ENCOUNTER} 02:00
ENVOYÉ PAR :
{NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère,

    Nous avons vu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}.

    Anamnèse
    ---------
    03-04-{DATE_HISTORY} : suspicion initiale {DIAGNOSIS}
    06/{DATE_HISTORY} : confirmation via {DX_TEST} ! Depuis lors fatigue,
    prise de poids, intolérance au froid. ATCD {DX_ABBREV}. {RELATIVE_RELATION} ({NAME_RELATIVE}) :
    {DX_EPONYM} à 55 ans Co {DX_NUMERIC} mg/dl le {DATE_ENCOUNTER},
    légèrement élevé {DX_ABBREV} valeurs normales. Pas de {DX_HOMOGRAPH}
    rapporté. Depuis peu, peau sèche et perte de cheveux, constatées par {HONORIFIC}
    elle-même. En lien avec {SPECIALTY}, symptômes réapparus. Pas de médication
    à domicile enregistrée. Pas d'allergie connue. {PRONOUN_SUBJ} signale des difficultés de
    concentration, surtout en fin d'après-midi. Pas d'insomnie. Pas de palpitations. Pas de
    douleur, pas de dyspnée. Pas de diarrhée ni de constipation. Pas de polyurie ou de polydipsie.
    Pas de traumatisme, pas d'infection récente. Pas de médication en dehors de
    {DX_DRUG}. Anamnèse gynécologique : ménopause à {DX_NUMERIC} ans. Pas
    de THS. Antécédents : {DX_ABBREV} diabète, hypercholestérolémie. Pas
    d'antécédent cardiovasculaire. Problématique psychiatrique : légère anhédonie,
    suivie de {DX_CODESWITCH} depuis {DATE_HISTORY}. Social : vit en
    solitaire, reçoit de l'aide d'un service à domicile pour le ménage. Familial : mère avec
    {DX_EPONYM}, père décédé à 72 ans après {DX_HOMOGRAPH}.
    Pas de tabac, pas d'alcool. Pas de sport, mode de vie sédentaire.

    Médication actuelle
    ----------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - {DX_DRUG_2}, 20 mcg, {DX_NUMERIC}, le matin
    Aucun traitement à domicile enregistré

    Examens techniques
    -----------------------
    TSH : {DX_NUMERIC} mU/L (↑) fT4 : 8,0 pmol/L (n) Anticorps anti-TPO : positifs
    {DX_TEST} : négatif pour {DX_CODESWITCH} Écho
    {DX_ANATOMY} : diffusément réduite, parenchyme hypoéchogène ECG : rythme sinusal, {DX_ABBREV}
    Biochimie : normale, {DX_ABBREV} {DX_NUMERIC}

    Conclusion
    -------
    Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} susmentionné a été vu {DX_ABBREV} symptômes persistants malgré
    le traitement.
    --> Ajustement de la dose de {DX_DRUG_2} à {DX_NUMERIC} mcg/j, nouveau contrôle
    {DX_TEST} dans 6 semaines.
    --> Initier {DX_DRUG_2} {DX_ABBREV} hypothyroïdie progressive.
    --> Arrêt de {DX_DRUG_2} {DX_ABBREV} manque d'efficacité.

    Conseils
    ------
    {PRONOUN_SUBJ} connaît le {TELEFOON} pour toute question. Retirer {DX_DRUG_2} en cas
    d'intolérance.
    --> Prochain contrôle en consultation {SPECIALTY} dans trois mois.
    --> En cas de saignement ou de douleur, nous contacter immédiatement.
    Formulaire d'avis soumis {DX_ABBREV} pour dépistage {DX_EPONYM}.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}
    {NAME_DOCTOR_4}
    {NAME_DOCTOR_5}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:07
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'Bovengenoemde X patiente werd gezien' -> 'Le {PATIENT_NOUN_GENERIC} X susmentionne a ete vu' (invariant subject).",
]},

{
"template_hash": "c144ae81adf7f4e6", "letter_type": "", "specialty": "",
"masked_text_fr": """COURRIER
PATIENT : RESPONSABLE : DATE :
{NAME_PATIENT} {NAME_RESPONSIBLE} {DATE_ENCOUNTER} 02:00
INSZ{INSZ} RIZIV{RIZIV} ENVOYÉ PAR
:
{NAME_DOCTOR_SENDER}
Contenu du rapport
{ORGANIZATION}
Médecine physique
Le {PATIENT_NOUN_GENERIC} susmentionné a été vu au service de Médecine physique et
réadaptation le {DATE_HISTORY} et le {DATE_VALIDATION}.
Motif de consultation :
------------
Douleurs persistantes aux deux épaules, toujours récidivantes après
infiltrations.
Également douleur nocturne et douleur à l'élévation.
Ne signale pas de perte de mobilité.
État au {DATE_VALIDATION} :
------------------
Ressent désormais plus de gêne au niveau de l'épaule gauche qu'avant {DX_ABBREV}
A du mal à s'allonger, se réveille souvent à cause des douleurs.
Côté gauche également plus de gêne qu'avant. Aucun effet de l'étoricoxib.
Examen clinique :
-------------------
{DX_CODESWITCH}
{DX_CODESWITCH} des deux côtés
Mobilité passive et active conservée
Examen technique :
------------------
Écho épaule bilatérale (pendant la consultation) :
- pas de liquide intra-articulaire autour du tendon du biceps, aspect normal
de la structure tendineuse {DX_ANATOMY} - Aspect normal {DX_ANATOMY}
- Aspect gonflé de la bourse subacromio-deltoïdienne, compatible avec une bursite
- Aspect fortement gonflé du tendon sus-épineux, tant sur la partie antérieure que postérieure :
aspect de tendinose
- Aspect normal {DX_ANATOMY}
- Pas de liquide intra-articulaire au niveau de l'articulation AC, contour osseux régulier
Conclusion :
--------
Tendinose du sus-épineux bilatérale avec gonflement bursal à gauche +
En concertation avec le {PATIENT_NOUN_GENERIC}, infiltration sous-acromiale avec {DX_NUMERIC} depomedrol des deux côtés,
en complément {DX_NUMERIC} {DX_ABBREV} sans effet net.
{DX_ABBREV} {DX_ABBREV} à gauche n'a pas non plus apporté d'amélioration pour le {PATIENT_NOUN_GENERIC}, qui ressent désormais
une gêne progressivement croissante.
--> infiltration sous-acromiale épaule gauche, IRM à planifier en l'absence
d'amélioration
Bien confraternellement
{NAME_DOCTOR}
Médecine physique et réadaptation
Cordialement, également au nom de
{NAME_DOCTOR_2} {NAME_DOCTOR_3}
{NAME_DOCTOR_3}
{NAME_DOCTOR_4}
{NAME_DOCTOR_5}
{NAME_DOCTOR_2}
{NAME_DOCTOR_5}
Ce rapport a été validé électroniquement par {NAME_DOCTOR_2} le {DATE_HISTORY}
Validation : {DATE_HISTORY} 11:20
---------------------------------------------------------------------------
{STREET} T {TELEFOON}
{STREET} T {TELEFOON} {STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "SIGNIFICANT SOURCE CORPUS BUG FOUND AND FIXED: the Dutch original has a real scored ADDRESS/STREET span ('Kasteelvest 175, 2000 Antwerpen') spliced INSIDE the middle of the word 'passend' (fitting/consistent-with), producing 'pKasteelvest 175, 2000 Antwerpennd bij bursitis' in all 93 real training documents for this template -- confirmed directly against train.jsonl's span offsets. This is a genuine pre-existing span-boundary corruption in the shipped Dutch training data (likely a PDF-column-extraction artifact from a real letterhead bleeding into body text), not something introduced by this project. The French version drops this corrupted mid-word address entirely and writes the clean, grammatically correct sentence ('...compatible avec une bursite') instead of reproducing the corruption -- the template's other STREET occurrences in the standard footer block are untouched.",
    "Rule 5 applied: bare 'Iom patiente' / 'voor patiente' -> '{PATIENT_NOUN_GENERIC}'.",
]},

{
"template_hash": "c85e68c6e87abf64", "letter_type": "spoedverslag", "specialty": "Gastro-enterologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                  {NAME_RESPONSIBLE}                   {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère,

    Nous avons vu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation de gastro-entérologie le
    {DATE_ENCOUNTER}.

    Motif de consultation :
    -----------
    {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM} ! {DX_ABBREV} diabète
    sucré Problématique psychiatrique {DX_ABBREV} symptômes persistants

    Antécédents familiaux :
    -----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à 58 ans

    Allergies :
    --------
    Pas d'allergie connue

    Traitement à l'admission :
    ------------------
    - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 500 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h
    Aucun traitement à domicile enregistré

    Anamnèse :
    ---------
    Orientation par {NAME_RELATIVE} {DX_ABBREV} douleurs abdominales persistantes.
    {PRONOUN_SUBJ} rapporte un transit variable, depuis {DX_NUMERIC} mois. ATCD {DX_ABBREV}.
    Pas de perte de poids. Symptômes temporairement améliorés sous {DX_DRUG_2},
    mais récidive à l'arrêt. Depuis lors, diarrhée avec mucus, pas de
    {DX_HOMOGRAPH}. Pas de plainte nocturne.

    Examen clinique :
    -------------------
    Abdomen : souple, non douloureux à la palpation, pas de {DX_ANATOMY} ! Pas
    d'hépatosplénomégalie. Bruits intestinaux normaux. {DX_TEST} : négatif

    Examen technique :
    --------------------
    Coloscopie {DATE_ENCOUNTER} : muqueuse iléale et colique {DX_ABBREV}, biopsies prélevées
    CT abdominal : pas d'anomalie constatée Laboratoire : calprotectine
    fécale élevée, CRP normale

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir :

    Diarrhée chronique sans signe d'alarme. Biopsies en cours. Les symptômes
    évoquent un syndrome du côlon irritable, mais une étiologie inflammatoire n'est pas encore
    exclue. {DX_CODESWITCH} est pris en compte.

    --> Attendre l'histologie.
    --> Si négatif : débuter {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    --> Contact via {TELEFOON} en cas d'aggravation.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:32
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 4 applied: dropped 'mevrouw' before {NAME_RELATIVE} ('Verwijzing via mevrouw {NAME_RELATIVE}') -- HONORIFIC is bound to the PATIENT's sex in the Case dataclass, not the relative's, so it would be unsafe here regardless of whether RELATIVE_RELATION appears in the same sentence.",
    "'haar klachten passen bij' (PRONOUN_POSS) -> 'Les symptomes evoquent' (dropped possessive).",
]},
]

def main():
    out_path = "translated_templates_fr_batch7.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
