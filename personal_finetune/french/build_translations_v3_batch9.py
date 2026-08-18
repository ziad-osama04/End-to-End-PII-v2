# -*- coding: utf-8 -*-
"""Batch 9: 4 more templates."""
import json

TEMPLATES = [
{
"template_hash": "f8b4c0e7ba6ae559", "letter_type": "consultatiebrief", "specialty": "Cardiologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                 {NAME_RESPONSIBLE}                    {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère

    Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en
    consultation en {SPECIALTY}.

    Anamnèse :
    ---------
    {DATE_HISTORY} : {DIAGNOSIS} ! Asymptomatique depuis ± 6 mois,
    gêne pectorale à l'effort. {DX_TEST}
    orientation {DX_ABBREV} suspicion de {DX_EPONYM}. Pas de dyspnée, pas d'orthopnée,
    pas de palpitations rapportées. {PRONOUN_SUBJ} mentionne toutefois une condition physique diminuée {DX_ABBREV}
    {DX_ABBREV}. Conserve {DX_DRUG} à domicile, usage sporadique.

    Médication actuelle :
    ------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    Aucun traitement à domicile enregistré

    Examens techniques :
    --------------------------
    ECG : rythme sinusal normal, {DX_CODESWITCH} Échographie
    {DX_ANATOMY} : légère hypokinésie apicale, FE {DX_NUMERIC} % Test d'effort sur tapis
    négatif {DX_ABBREV} ischémie {DX_HOMOGRAPH} !

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir : {DIAGNOSIS} stable,
    asymptomatique sous traitement. Lésion de l'artère coronaire droite {DX_ABBREV} {DX_NUMERIC}
    --> Poursuite du traitement médical optimal, pas d'indication d'intervention.

    Conseils :
    --------
    Contrôle en cas d'aggravation des symptômes ou de nouvelle symptomatologie. Suivi dans 6
    mois en {SPECIALTY}. {TELEFOON} pour toute question. Conservation de
    {DX_DRUG_2} conseillée {DX_ABBREV} possible {DX_HOMOGRAPH}.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 15:42
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'{DX_TEST} verwezen' (gendered-participle trap) -> 'orientation {DX_ABBREV} suspicion de' (noun-based).",
]},

{
"template_hash": "f926f88287e7a51a", "letter_type": "opvolgbrief", "specialty": "Oftalmologie",
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

    Motif d'admission :
    -----------------
    Vision floue à droite depuis {DATE_HISTORY} !

    Antécédents :
    -----------------
    {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM}, traitement par {DX_DRUG}
    déjà instauré {DX_ABBREV} diabète de type 2 {DX_ABBREV} traumatisme oculaire gauche
    (1985)

    Antécédents familiaux :
    -----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : glaucome à un âge avancé

    Allergies :
    --------
    Pas d'allergie connue

    Traitement à l'admission :
    ------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 0,5% susp., 1 goutte i.o.d., {DX_NUMERIC}
    - paracétamol 1g, 1 comp, 4/j mwt

    Évolution :
    ---------
    Les symptômes persistent malgré un essai thérapeutique par {DX_DRUG_2}.
    Acuité {DX_ABBREV} : 0,3 (auparavant 0,6), {DX_ABBREV} : 0,8. Pas de douleur, pas de diplopie.
    {DX_TEST} montre une progression {DX_ANATOMY} ! {DX_ABBREV}
    stabilisation de {DIAGNOSIS} via {DX_HOMOGRAPH}
    non atteinte.

    Médication de sortie :
    -----------------
    - {DX_DRUG_2}, 0,5% susp., 1 goutte i.o.d., {DX_NUMERIC}
    - {DX_DRUG_2}, {DX_NUMERIC}, le matin
    - pommade vitamine A, 1 application, soir

    Conclusion :
    --------
    Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} signale une baisse visuelle progressive à droite {DX_ABBREV}
    {DIAGNOSIS}. État de l'œil gauche stable.
    {DX_CODESWITCH} confirme la nécessité d'un ajustement du régime.
    --> Arrêt de {DX_DRUG_2}, passage à un régime {DX_NUMERIC}.
    --> Suivi en polyclinique {SPECIALTY} dans 6 semaines.
    --> Orientation vers {NAME_RELATIVE} {DX_ABBREV} consultation {RELATIVE_RELATION}.
    Aucun traitement à domicile enregistré en dehors de ce qui est prescrit. Contact
    téléphonique possible via {TELEFOON} en cas d'aggravation aiguë.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}
    {NAME_DOCTOR_4}
    {NAME_DOCTOR_5}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:09
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'reeds behandeld met X' (gendered-participle trap) -> 'traitement par X deja instaure' (agrees with invariant 'traitement').",
    "Rule 4 applied: dropped 'de heer' before {NAME_RELATIVE} ('Doorverwijzing naar de heer {NAME_RELATIVE} {RELATIVE_RELATION} consult').",
    "'zijn klachten aanhoudend' (PRONOUN_POSS) -> 'Les symptomes persistent' (dropped possessive).",
]},

{
"template_hash": "fa8f7b513e07f53b", "letter_type": "consultatiebrief", "specialty": "Urologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Anamnèse : --------- 03-04-{DX_NUMERIC} : début des symptômes mictionnels, fréquence et urgence 10/2023 : échographie abdominale {DX_ABBREV} douleur de flanc – masse {DX_ANATOMY} massive incidentelle ! signalée {DIAGNOSIS} connu depuis {DATE_HISTORY}, {DX_ABBREV} diabète de type 2 Il s'agit d'une deuxième consultation après orientation par le médecin traitant {DX_ABBREV} hématurie macroscopique persistante ATCD {DX_ABBREV}, statut post RTUP en 2018 pour hypertrophie bénigne de la prostate Plus de tabac depuis 5 ans, {DX_ABBREV} consommation modérée d'alcool ({DX_ABBREV}) Antécédents familiaux : ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : cancer du rein à 68 ans Allergies : --------- Pas d'allergie connue Médication actuelle : ------------------ - {DX_DRUG}, 5 mg, {DX_NUMERIC}, {DX_NUMERIC} - Metformine 850 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h - Atorvastatine 20 mg, {DX_NUMERIC}, soir - {DX_DRUG_2}, PRN, en cas de douleur Aucun traitement à domicile enregistré Examens techniques : -------------------------- {DX_TEST} : urodynamique anormale – attention à l'hyperactivité détrusorienne IRM prostate : foyer suspect en zone apicale droite, PI-RADS 4 CT-thorax-abdomen-pelvis : pas de métastase mise en évidence PSA : {DX_NUMERIC} ng/ml (en hausse par rapport à la mesure précédente de 4,2) {DX_CODESWITCH} : nécessaire pour différencier tumeur vs prostatite Conclusion : -------- Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} signale des troubles mictionnels progressifs avec hématurie macroscopique d'apparition récente. Statut post intervention chirurgicale pour HBP, suivi actuel {DX_ABBREV} suspicion de {DIAGNOSIS}. L'imagerie montre une lésion préoccupante au niveau de la prostate ! Avec des valeurs de PSA élevées. Pas de dissémination extraprostatique actuellement. --> Procédure de biopsie par voie échographique transrectale envisagée, planification en concertation. --> Consultation en concertation multidisciplinaire (COM-oncologie) planifiée le {DATE_ENCOUNTER}. --> Contact via {TELEFOON} en cas de symptômes aigus s'aggravant. Conseils : -------- - Échantillon urinaire (cytologie) envoyé au laboratoire - Suivre le protocole {DX_EPONYM} {DX_ABBREV} suivi après biopsie - Orienter vers un généticien clinique si un regroupement familial est constaté - Nouvelle consultation en {SPECIALTY} dans les 4 semaines suivant la COM

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 14:28
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 5 applied: 'De X patient meldt' -> 'Le {PATIENT_NOUN_GENERIC} X signale'.",
]},

{
"template_hash": "fdfbaa890459c4aa", "letter_type": "ontslagbrief", "specialty": "Endocrinologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                  {NAME_RESPONSIBLE}               {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. Motif de consultation -------- {DX_NUMERIC}/2023 : {DIAGNOSIS} ! Co diabète de type 2 {DX_EPONYM} : détérioration progressive de la fonction rénale, DFG en baisse jusqu'à {DX_NUMERIC} ATCD {DX_ABBREV}, hypercholestérolémie Antécédents familiaux --------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à un jeune âge, décès à {DOB} Allergies -------- Pas d'allergie connue Traitement à l'admission ------------------- - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 0,5 comp, {DX_NUMERIC}, matin - {DX_HOMOGRAPH}, s.i.d., le matin à jeun État ------ {PATIENT_NOUN_MARKED} {AGE_ADJ} signale de la fatigue, une prise de poids et une intolérance au froid. {PRONOUN_SUBJ} a depuis {DX_NUMERIC} des problèmes de concentration, y compris pendant le repos nocturne. Symptômes persistants malgré une substitution optimale selon le suivi externe. Pas de symptôme d'hypoglycémie ni de trouble cardiaque. Plus de constipation. La médication thyroïdienne a été ajustée ailleurs sans réponse claire. Examen clinique ------------------ TSH : {DX_TEST} – augmentation jusqu'à {DX_NUMERIC} mU/L ! fT4 : légèrement diminuée {DX_ANATOMY} : voix subtilement affaiblie, cheveux s'affinant, peau sèche Pouls : 58 battements/min, régulier TA : 124/78 mmHg Examen technique ------------------- {DX_TEST} (le {DATE_ENCOUNTER}) : TSH ↑↑, fT4 ↓ Anticorps anti-TPO positifs → origine auto-immune probable Échographie {DX_ANATOMY} : organe diffusément réduit, structure hétérogène Créatinine : normale, DFGe stable à {DX_NUMERIC} HbA1c : {DX_NUMERIC}% {DX_CODESWITCH} Conclusion -------- Le {PATIENT_NOUN_GENERIC} susmentionné a été vu {DX_ABBREV} symptômes persistants dans le cadre d'un {DIAGNOSIS} connu. Malgré un dosage adéquat de {DX_DRUG_2}, la TSH reste élevée. Problème d'observance possible ? L'observance thérapeutique est confirmée par {NAME_RELATIVE}, mais le moment de la prise n'est pas optimal (souvent après le petit-déjeuner). Prise désormais ajustée à {DX_NUMERIC}, 30 min avant le petit-déjeuner, avec un verre d'eau. --> Nouveau contrôle en {SPECIALTY} dans 6 semaines pour réévaluation des symptômes et TSH/fT4 --> En l'absence d'amélioration : envisager un changement vers {DX_DRUG_2} ou analyser le moment de la prise en lien avec {DX_HOMOGRAPH} --> Éducation donnée {DX_ABBREV} prise de médication, alimentation et interactions --> Aucun ajustement d'autre traitement nécessaire Aucun traitement à domicile enregistré en dehors de ce qui est mentionné

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 12:15
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'overleden op {DOB}' (gendered-participle trap on RELATIVE_RELATION) -> 'deces a {DOB}' (noun-based).",
    "Rule 4 applied: dropped 'mevrouw' before {NAME_RELATIVE} ('therapietrouw wordt bevestigd door mevrouw {NAME_RELATIVE}').",
    "'haar therapietrouw' (PRONOUN_POSS) -> 'L'observance therapeutique' (dropped possessive).",
]},
]

def main():
    out_path = "translated_templates_fr_batch9.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
