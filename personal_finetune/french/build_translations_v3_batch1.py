# -*- coding: utf-8 -*-
"""
Rebuild of the 10 already-translated templates against the v3 recovery
(which properly parametrizes SPECIALTY/DIAGNOSIS/RELATIVE_RELATION/DX_*
that v1 had frozen as literal text -- see STYLE_RULES.md for the four
grammar-safety rules discovered and applied here).
"""
import json

TEMPLATES = [
{
"template_hash": "085ee68a2d15cebb", "letter_type": "consultatiebrief", "specialty": "Pneumologie",
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

 Cher confrère UNITÉ : 14612 DATE : {DATE_ENCOUNTER} ORIGINE : mixte ÂGE : {AGE} TAILLE 178,2 cm POIDS 108,8 kg IMC 34,272 TABAGISME : non connu Motif de consultation : ----------- {DATE_HISTORY} : début de dyspnée à l'effort, plainte progressive depuis 03/2023 : toux accrue avec expectorations, {DX_ABBREV} {DX_DRUG} orientation par le médecin traitant {DX_ABBREV} avec {DIAGNOSIS} et suspicion de {DX_EPONYM} ! Antécédents : ----------------- 15/04/{DOB} : {DIAGNOSIS} 06/2020 : première exacerbation liée au suivi en {SPECIALTY} {DX_ABBREV} diabète de type 2, contrôlé {DX_ABBREV} réanimation après anaphylaxie ({DX_DRUG_2}) Antécédents familiaux : ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : fibrose pulmonaire à 70 ans père : BPCO, fumeur de longue date Allergies : ---------- Pas d'allergie connue Traitement à l'admission : ------------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - salbutamol (inhalation) 100 mcg, si besoin - tiotropium, 1 gélule, {DX_NUMERIC}, le matin - {DX_DRUG_2}, 5 mg, {DX_NUMERIC}, 9h Anamnèse : ------- {HONORIFIC} {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ} avec {DIAGNOSIS}, se présente pour un essoufflement persistant {DX_ABBREV} la montée des escaliers ou la marche rapide. Situation stable selon le dernier contrôle en {DATE_ENCOUNTER}. Pas de fièvre ni de sueurs nocturnes. Expectorations : parfois grisâtres, jamais sanglantes. Pas de perte de poids. {PRONOUN_SUBJ} utilise régulièrement les inhalateurs, mais rapporte « peu d'effet » depuis {DX_NUMERIC} mois. Pas de plainte d'orthopnée ni de DPN. Examen clinique : ------------------- état général : stable, pas de cyanose ! thorax : expansion symétrique, percussion claire, {DX_TEST} poumons : râles à l'auscultation en base gauche, reste du murmure vésiculaire {DX_HOMOGRAPH} FC : régulière, {DX_ANATOMY} {DX_ABBREV} abdomen : souple, pas d'hépatosplénomégalie Examens techniques : -------------------- RX thorax {DATE_ENCOUNTER} : hypertransparence discordante à droite, pas d'infiltrats CT-thorax (05/{DX_NUMERIC}) : bronchectasies affectant la base droite, wall thickening, {DX_CODESWITCH} spirométrie : VEMS 68 % prédit, rapport VEMS/CVF diminué → obstruction {DX_ABBREV} Conclusion : -------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en {SPECIALTY} le {DATE_ENCOUNTER}. À retenir : {DIAGNOSIS} stable, pas d'exacerbation aiguë. Réponse cependant limitée au traitement actuel. {DX_EPONYM} reste un diagnostic différentiel au vu des résultats du CT. Traitement à domicile enregistré : voir ci-dessus. --> poursuivre le traitement de base actuel --> ajout à envisager : corticostéroïde inhalé (fluticasone) lors de la réévaluation --> orientation vers la kinésithérapie respiratoire {DX_ABBREV} {DX_DRUG_2} --> consultation de contrôle dans trois mois ou plus tôt en cas d'aggravation (!)

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:57
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: SPECIALTY/DIAGNOSIS were frozen literal text under v1 recovery (unscored fields) -- now properly slotted.",
    "Rule 1 applied: 'en {SPECIALTY}' never 'de/la {SPECIALTY}' (SPECIALTIES includes vowel-initial 'ORL', breaks elision).",
    "Rule 2 applied: 'avec {DIAGNOSIS}' / bare '{DIAGNOSIS}' label instead of 'la/le {DIAGNOSIS}' or '{DIAGNOSIS} connue' (DIAGNOSES mixes gender and vowel-initial values e.g. asthme/eczema/endometriose).",
    "Conclusion restructured active-voice 'Nous avons revu X, {PATIENT_NOUN_MARKED} de Y, en {SPECIALTY}...' -- avoids gendered passive participle.",
]},

{
"template_hash": "11369ce1f2beb381", "letter_type": "opvolgbrief", "specialty": "Reumatologie",
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

    Antécédents :
    -----------------
    {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM} ! Polyarthrite
    rhumatoïde depuis 2015, {DX_NUMERIC} selon les plaintes Parfois iridocyclite
    intermittente, suivi ophtalmologique en cours

    Antécédents familiaux :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_TEST} le {DOB}

    Allergies :
    ---------
    Pas d'allergie connue

    Anamnèse :
    ---------
    {PATIENT_NOUN_MARKED} de {AGE_ADJ} rapporte une raideur progressive des mains et
    des poignets, surtout le matin. Durée : 1h30. Sous {DX_DRUG} depuis
    {DATE_HISTORY}, mais aggravation des symptômes ces dernières semaines. ATCD
    {DX_ABBREV}. Pas de symptômes systémiques tels que fièvre ou perte de
    poids. Pas de {DX_HOMOGRAPH}. A suivi de la kinésithérapie, sans
    {DX_CODESWITCH}. Symptômes limitant les AVQ.

    Examen clinique :
    -------------------
    Mains : tuméfaction symétrique MCP 2-5 et IPP 2-4, {DX_ANATOMY} positif !
    Pas de déviation ulnaire. Poignet : douloureux à l'extension passive, {DX_ABBREV} de
    faiblesse. Coudes : {DX_ABBREV}. {DX_TEST} négatif Les deux genoux : choc
    rotulien, gonflés, mais non douloureux. Pas d'instabilité.

    Examens techniques :
    ------------------------
    Écho mains rhumatoïdes (réf. {DX_DRUG_2}) : synovite grade 2-3 MCP,
    IPP, poignets. Rx mains (réf. {DX_CODESWITCH}) : érosions à la base
    des phalangettes, {DX_ABBREV} progression par rapport à {DATE_HISTORY}. CRP : 8 mg/l (réf.
    <5), VS : 22 mm/h (réf. <20) FR : positif (>200 UI), anti-CCP : 320 U/ml

    Conclusion :
    -------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en consultation en
    {SPECIALTY} le {DATE_ENCOUNTER}. À retenir : {PRONOUN_SUBJ} présente une polyarthrite
    inflammatoire progressive avec limitation fonctionnelle et activité
    biochimique. Pas de {DX_HOMOGRAPH}, sérologie positive en revanche.

    --> Initier méthotrexate 15 mg sc 1x/sem, débuter folate 5 mg 1x/sem 1 jour
    après le MTX.
    --> Passage à {DX_DRUG_2} 7,5 mg/j {DX_ABBREV} profil inflammatoire et risque
    de progression.
    --> Kinésithérapie sur mesure, {DX_ABBREV} demande.
    --> contrôle en {SPECIALTY} dans 3 mois {DX_ABBREV} réponse.

    Traitement à domicile :
    -------------
    - {DX_DRUG_2}, 1 comprimé, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1-0-1, {DX_NUMERIC} 14h 20h

    Aucun traitement à domicile enregistré en dehors de ce qui précède. {TELEFOON} pour
    toute question.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 12:35
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted (were frozen in v1).",
    "'Wij zagen uw patient X' -> 'Nous avons vu votre {PATIENT_NOUN_GENERIC} X' (reuses DEMO_TEMPLATE's own established generic-noun convention).",
]},

{
"template_hash": "11dc809f9e038c5a", "letter_type": "consultatiebrief", "specialty": "Oncologie",
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

    Anamnèse :
    ----------
    {PRONOUN_SUBJ} rapporte une fatigue progressivement croissante depuis 03/2024.
    Perte de poids d'environ {DX_NUMERIC} kg au cours des 2 derniers mois, sans régime.
    Pas de sueurs nocturnes rapportées. Auparavant légère douleur en fosse iliaque gauche, actuellement {DX_ABBREV}.
    ATCD {DX_ABBREV}, statut post traitement par {DX_EPONYM} (2018).
    Antécédents familiaux : {DX_ABBREV}-{DIAGNOSIS} chez {RELATIVE_RELATION} {NAME_RELATIVE}.
    {PRONOUN_SUBJ} travaille encore à temps partiel comme {DX_HOMOGRAPH}, surtout en administratif.
    Situation sociale : vit en solitaire, ne fume pas, consommation d'alcool occasionnelle. Pas de plainte
    de sang dans les urines ou les selles depuis le début de {DX_DRUG}. !
    Douleurs temporairement accrues après un cycle de chimiothérapie en {DATE_HISTORY}.

    Médication actuelle :
    -----------------
    - {DX_DRUG_2} (comp. 5 mg), 5 mg, {DX_NUMERIC}, 9h
    - Zytiga (comp. 500 mg), 500 mg, {DX_NUMERIC}, 7h à jeun
    - Prednisone (comp. 5 mg), 5 mg, {DX_NUMERIC}, {DX_NUMERIC} et 20h
    - {DX_DRUG_2} (injection 10 mg/ml), 10 mg, iv, q3sem
    - Paracétamol (comp. 1 g), 1 g, p.r.n. pour fièvre
    Pas d'allergie connue

    Examens techniques :
    ------------------------
    CT-abdomen {DATE_ENCOUNTER} : stabilisation des lésions {DX_ANATOMY}, pas de nouvelle
    anomalie hépatique ou ganglionnaire. PET-scan {DATE_HISTORY} : activité
    métabolique limitée dans la zone {DX_CODESWITCH}, compatible avec un
    résidu. Bilan sanguin complet : Hb {DX_NUMERIC} g/l (limite normale basse), plaquettes
    210, leuco {DX_ABBREV}. Marqueurs tumoraux : PSA en baisse de 8,2 à 4,6 ng/ml depuis le
    dernier cycle. {DX_TEST} : {DX_ABBREV} à la palpation abdominale, pas
    d'hépatosplénomégalie. ECG : rythme sinusal, QTc {DX_ABBREV}, pas de
    troubles de la repolarisation. Biopsie {DX_ANATOMY} (dd. {DATE_HISTORY}) : confirme
    {DIAGNOSIS}, immunohistochimie positive pour le RA.

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, le {DATE_ENCOUNTER} {DX_ABBREV} suivi de
    {DIAGNOSIS} avec évaluation de la réponse au traitement. Le traitement
    se déroule selon le schéma, {DX_ABBREV} stabilisation clinique et radiologique. En raison
    de la fatigue persistante : vérifier les réserves en fer, envisager
    une induction par érythropoïétine si nécessaire.
    --> Poursuite du régime actuel avec {DX_DRUG_2} + {DX_DRUG_2} jusqu'au
    prochain contrôle.
    --> Planifier une répétition du PET-scan dans 12 semaines (dd. {DX_NUMERIC}).
    --> Orienter vers un soutien palliatif {DX_ABBREV} charge de comorbidités {DX_ABBREV}.

    Conseils :
    -------
    {PRONOUN_SUBJ} peut appeler entre-temps au {TELEFOON} en cas d'aggravation aiguë, de fièvre
    >38,5°C ou d'hématurie. La coordination du traitement reste du ressort de l'oncologie ; pas
    de changement du traitement à domicile. Dernière consultation : voir rapport dd. {DATE_HISTORY}.
    Le {PATIENT_NOUN_GENERIC} susmentionné sera automatiquement convoqué pour une consultation de suivi.
    Aucun traitement à domicile enregistré en dehors de la liste ci-dessus.

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

    Validation : {DATE_VALIDATION} 11:36
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "'woont alleen' (invariant Dutch adjective) -> 'vit en solitaire' not 'vit seul(e)' -- 'solitaire' is gender-invariant French, avoids a bracket stopgap.",
    "'Bovengenoemde patient ... uitgenodigd' -> 'Le {PATIENT_NOUN_GENERIC} susmentionné sera ... convoqué' (reuses the invariant-masculine-generic-as-subject fix already validated elsewhere in this project).",
]},

{
"template_hash": "1a45c72c46030984", "letter_type": "spoedverslag", "specialty": "Endocrinologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                 {NAME_RESPONSIBLE}              {DATE_ENCOUNTER} 02:00
INSZ{INSZ}          RIZIV{RIZIV}             ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. Antécédents : ----------------- {DOB} : naissance sans particularité, {DX_ABBREV} {DX_ABBREV} 05-2018 : diagnostic de {DIAGNOSIS} établi chez {NAME_RELATIVE}, {DX_ABBREV}. {DX_EPONYM} 12-2020 : début {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC}, {DX_ABBREV} hba1c ↑ 03-2023 : {DX_ABBREV} diabète type 2 et obésité, {DX_ABBREV} syndrome métabolique ! {DX_NUMERIC} : courbe glycémique récente dans les limites Allergies : --------- Pas d'allergie connue Anamnèse : --------- {PATIENT_NOUN_MARKED} de {AGE_ADJ} signale une fatigue depuis {DATE_HISTORY}, surtout le matin Pas de palpitations, tremblements ou perte de poids. Appétit normal. ATCD dyslipidémie et NAFLD. Pas de consommation d'alcool, {DX_ABBREV} fumeur. Anamnèse familiale positive pour {DIAGNOSIS} ({RELATIVE_RELATION} : {NAME_RELATIVE}) {DX_HOMOGRAPH} est mentionné, mais sans confirmation {DX_TEST} Examen clinique : ------------------- Cou : faciès euthyroïdien, pas d'exophtalmie ! TSH : 0.02 mU/L (réf 0.4–4.0), fT4 25 pmol/L (réf 10–20) → hyperthyroïdie ! {DX_ANATOMY} : hypertrophie diffuse, non douloureuse, pas de nodule Cardio : rythme cardiaque régulier, 94 bpm, tension 138/82 mmHg Réflexes : {DX_ABBREV}, réflexes vifs Conclusion : -------- Le {PATIENT_NOUN_GENERIC} susmentionné a été revu {DX_ABBREV} hyperthyroïdie persistante depuis {DATE_ENCOUNTER}, malgré le début de {DX_DRUG_2} lors de la première consultation en {SPECIALTY}. Le dernier contrôle {DX_TEST} montre une surproduction encore progressive. --> référence en médecine nucléaire pour évaluation {DX_CODESWITCH} --> tests TPO-ab et TRAb en cours --> traitement temporaire par {DX_DRUG_2} (comp. 10 mg), 10 mg, {DX_NUMERIC}, 9h {PRONOUN_SUBJ} contacte le {TELEFOON} en cas de fièvre ou de mal de gorge !

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

    Validation : {DATE_VALIDATION} 09:23
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "Rule 4 applied: dropped hardcoded 'de heer' before the FIRST {NAME_RELATIVE} mention ('diagnostic de X etabli chez {NAME_RELATIVE}') -- this relative's honorific would contradict the LATER {RELATIVE_RELATION} slot on the same sampled value whenever that relation is feminine (Mere/Soeur/Tante/...).",
    "'Bijenkorf:' (garbled Dutch OCR-ish header) rendered contextually as 'Cou :' (neck exam), matching the actual clinical content that follows (thyroid/exophthalmos exam).",
    "Reuses the already-validated 'Le {PATIENT_NOUN_GENERIC} susmentionne a ete revu' fix for this exact template's previously-found passive-participle bug.",
]},

{
"template_hash": "2299d2f326855e74", "letter_type": "spoedverslag", "specialty": "Orthopedie",
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
    -----------
    {DATE_HISTORY} : chute de hauteur (>2 mètres) lors de travaux de jardinage 03/2024 :
    {DIAGNOSIS} cheville droite, plâtrée à l'extérieur Douleur
    chronique du genou droit depuis 2019 ({DX_ABBREV} {DX_EPONYM})

    Antécédents :
    -----------------
    Polyarthrite rhumatoïde depuis l'âge de 58 ans. {DIAGNOSIS} (T-score
    -2,8). Lésion articulaire post-traumatique du genou gauche dans l'enfance. ATCD {DX_ABBREV}

    Antécédents familiaux :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_HOMOGRAPH} à un âge avancé Sans particularité
    cardiovasculaire chez les autres membres de la famille

    Allergies :
    ----------
    Pas d'allergie connue

    Traitement à l'admission :
    -------------------
    - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC}
    - Paracétamol 1g, 4/j, prn
    - {DX_DRUG_2}, 0,5 comp, {DX_NUMERIC}, {DX_NUMERIC}
    - Calcium + vitamine D, {DX_NUMERIC}

    Anamnèse :
    -------
    Douleur lombaire aiguë depuis {DATE_ENCOUNTER}, apparue après avoir soulevé un seau d'eau. Douleur
    irradiant vers la jambe gauche jusqu'au pied, ! caractère neurologique. Claudication
    intermittente présente depuis des années, désormais aggravée. Scooter électrique mobile pour
    usage domestique. {PRONOUN_SUBJ} suspecte une fracture {DX_ABBREV} ostéoporose. Pas de trouble
    urinaire ou intestinal. Pas de fièvre. Pas de traumatisme {DX_NUMERIC}. Reste mobile avec rollator.
    Pas de chute sur la hanche la semaine dernière.

    Examen clinique :
    -------------------
    Général : {AGE_ADJ}, mobilité limitée {DX_ABBREV} douleur, démarche dandinante ! Lombaire :
    douleur à la pression L4-L5, paravertébrale. Lasègue négatif à gauche. Membres :
    déficit sensitif dermatome L5 gauche. Réflexe rotulien ↓ à gauche. Démarche
    correspondante, antalgique. {DX_TEST}. Amplitude passive de la hanche :
    {DX_ABBREV}. {DX_ANATOMY} intact.

    Examen technique :
    --------------------
    Radiographie thorax : rien d'aigu visible. ECG : tachycardie sinusale 104/min, {DX_ABBREV}
    ischémie. CT lombo-sacré : fracture du corps de L4 (compression 40 %), type
    ostéoporotique. Pas de compression médullaire. IRM non indiquée actuellement.

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, {DX_ABBREV} lombalgie subaiguë avec composante
    neurologique. Au vu de {DX_CODESWITCH} et de l'imagerie : {DIAGNOSIS}.
    Prise en charge de la douleur adéquate mais soulagement insuffisant.
    Co-diagnostic de myopathie liée à {DX_DRUG_2} non exclu.
    Consentement demandé à {HONORIFIC} {NAME_PATIENT} pour le suivi.

    Examens techniques :
    -----------------------
    RX thorax {DATE_ENCOUNTER} CT lombo-sacré {DATE_ENCOUNTER} Laboratoire : Hb 10,8, CRP 8,
    créatinine 78, Ca²⁺ 2,32

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:18
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "Rule 2 applied: 'Bekende {DIAGNOSIS} (T-score...)' rendered as a bare label '{DIAGNOSIS} (T-score...)' instead of '{DIAGNOSIS} connue' (gender-agreement trap).",
    "'zijn de heer toestemming gevraagd' (garbled Dutch, likely referring to the patient given PRONOUN_SUBJ=hij elsewhere in this same template) -> 'Consentement demande a {HONORIFIC} {NAME_PATIENT} pour le suivi.' using the patient's own HONORIFIC slot, dropping the stray 'zijn' fragment.",
]},

{
"template_hash": "2a857a0ab7554aff", "letter_type": "ontslagbrief", "specialty": "Urologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                   {NAME_RESPONSIBLE}               {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère

    Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en
    consultation en {SPECIALTY}.

    Motif de consultation
    --------
    {DATE_HISTORY} : {DIAGNOSIS} {DIAGNOSIS} ! Infections
    urinaires récidivantes depuis 2018 Co diabète de type 2

    Antécédents familiaux
    ---------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : cancer de la prostate à 72 ans. {RELATIVE_RELATION}
    également : {DX_ABBREV} sous {DX_DRUG}

    Allergies
    --------
    Pas d'allergie connue

    Traitement à domicile
    --------------
    Aucun traitement à domicile enregistré

    Traitement à l'admission
    -------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 200 mg, {DX_NUMERIC}, 9h
    - Paracétamol (comp. 1000mg), 1000mg, 3/j, {DX_NUMERIC}-14h-20h

    Anamnèse
    --------
    Orientation {DX_ABBREV} hématurie récidivante, depuis {DATE_HISTORY}. ATCD RTUP en 2020.
    Plus de dysurie, mais nycturie et gouttes persistantes. Pas de plainte
    fébrile. Pas de douleur lombaire. Pas de {DX_HOMOGRAPH}. Cathétérisme
    difficile en jan/{DX_NUMERIC} : urètre légèrement endommagé. Depuis lors, difficulté
    d'auto-cathétérisme. Plaintes de vidange incomplète. Pas de ténesme. Pas de
    {DX_CODESWITCH} rapporté.

    État
    ------
    {AGE_ADJ}, patient dans un état général stable. Pas de signe d'infection à
    l'admission. Pas d'œdème. Pas de TVJ augmentée. Conscient, orienté, mobile. Réflexe
    mictionnel normal.

    Examen clinique
    -------------------
    Abdomen : souple, non douloureux, pas de {DX_ANATOMY} Suspubien : non
    rempli, pas de ballonnement Génital : pas d'écoulement urétral, pas de
    {DX_TEST} Toucher rectal : prostate non hypertrophiée, pas de {DX_ABBREV}, pas de
    sang au doigt ! {DX_NUMERIC} cm entre le ballonnet de la sonde et le rétrécissement

    Examen technique
    ------------------
    - Créatinine : 87 µmol/L (stable)
    - Sédiment urinaire : leucocyturie +++, érythrocyturie ++++
    - Culture urinaire : E. coli >10^5, sensible à {DX_DRUG_2}
    - Écho abdominale : épaississement de la paroi vésicale, RPM 180ml, pas d'hydronéphrose
    - CT-abdomen : pas de cicatrice au niveau {DX_ANATOMY}, pas de niveau de {DX_DRUG_2}
    - Urodynamique : détrusor hyperactif, Qmax 9 ml/s, post-mictionnel 210 ml
    - Cystoscopie : petite trabéculation, pas de tumeur, pas de {DIAGNOSIS}

    Conclusion
    -----
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en consultation en
    {SPECIALTY} le {DATE_ENCOUNTER}. À retenir :

    Hématurie récidivante avec résultats urodynamiques évoquant une
    problématique obstructive. Pas de preuve de malignité à la cystoscopie. Symptômes
    en grande partie secondaires {DX_ABBREV} résidu. La situation du {PATIENT_NOUN_GENERIC} s'explique
    par une intervention antérieure et une lésion urétrale. Un traitement par
    {DX_DRUG_2} a été instauré {DX_ABBREV} infection avérée.

    --> Poursuite du traitement par {DX_DRUG_2} pendant {DX_NUMERIC} semaines.
    --> Technique de recathétérisme expliquée à {NAME_RELATIVE}.
    --> Débuter la rééducation via kinésithérapie ({DX_ABBREV}).
    --> Consultation {SPECIALTY} dans 6 semaines pour contrôle et éventuelle
    {DX_CODESWITCH}.
    --> En cas de récidive : réévaluation nécessaire {DX_ABBREV} {DX_ABBREV} et éventuelle
    {DX_HOMOGRAPH}.

    Contactez-nous en cas d'aggravation ou de fièvre : {TELEFOON}

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

    Validation : {DATE_VALIDATION} 11:34
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "Rule 4 applied: dropped 'de heer' before the second-mention {NAME_RELATIVE} ('technique de recatheterisme expliquee a {NAME_RELATIVE}').",
    "'zijn situatie' (his situation, PRONOUN_POSS -- deliberately not modeled in the French Case) -> 'La situation du {PATIENT_NOUN_GENERIC}' (full noun phrase, sidesteps the missing possessive slot).",
    "'hij werdt gestart op X' -> 'Un traitement par X a ete instaure' (invariant-noun-as-subject fix, matches the already-validated 'Un traitement par Depakine...' pattern from this project's earlier review pass).",
]},

{
"template_hash": "2aa05d5d272aa7ff", "letter_type": "verslag technisch onderzoek", "specialty": "Vaatheelkunde",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. Anamnèse : -------- 03/2022 : {DIAGNOSIS} ! {DX_EPONYM} {DX_ABBREV} {DX_HOMOGRAPH} depuis {DATE_HISTORY} ATCD {DX_ABBREV}, {DX_ABBREV} {DX_DRUG}. {DX_TEST} {DX_ABBREV} {DIAGNOSIS} {PRONOUN_SUBJ} signale une aggravation des douleurs à la marche, désormais après seulement 50 mètres. {NAME_RELATIVE} indique que {PRONOUN_SUBJ} ressent également, depuis la semaine dernière, un gonflement au niveau {DX_ANATOMY} ! Pas d'épisode de douleur nocturne ou de plainte au repos Antécédents familiaux : -------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à 68 ans {DX_DRUG_2} chez {NAME_RELATIVE} – {NAME_RELATIVE} garde rarement le contrôle de la situation Allergies : --------- Pas d'allergie connue Traitement à l'admission : -------------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h - Ascal (comp. 100mg), {DX_NUMERIC}, {DX_NUMERIC} Médication actuelle : ------------------ - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h - Ascal (comp. 100mg), {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2} crème, PRN Aucun traitement à domicile enregistré Examen clinique : ------------------- Douleur à la palpation {DX_ANATOMY} ! Gauche > droite {DX_TEST} positif à gauche, négatif à droite Pouls périphériques {DX_ABBREV}, duplex à évaluer Perfusion du pied : droite 0,52, gauche 0,41 ({DX_NUMERIC}) Remplissage capillaire : 4 secondes sous {DX_DRUG_2} Examens techniques : ----------------------- `-----------------------------` `| Test | Résultat |` `|-----------------+--------|` `| IPS | 0.63 |` `| IPS après effort| 0.48 |` `| duplex {DX_ANATOMY}| {DX_CODESWITCH}|` `| CT-angiographie | {DX_NUMERIC}|` `-----------------------------` Conclusion : -------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, {DX_ABBREV} claudication intermittente progressive. Gonflement {DX_ANATOMY}, s'aggravant sous {DX_DRUG_2}. Antécédent de {DX_EPONYM}. IPS bas, avec baisse après effort. {DX_TEST} confirme l'ischémie. {DX_DRUG_2} contribution possible à l'œdème périphérique. --> Envisager l'arrêt de la crème {DX_DRUG_2} {DX_ABBREV} effet limité et réactions locales --> Poser l'indication d'une revascularisation endovasculaire en {SPECIALTY} --> Orientation vers {SPECIALTY} pour planification ultérieure Conseils : -------- - Arrêt immédiat de la crème {DX_DRUG_2} - Nous contacter au {TELEFOON} en cas d'aggravation du gonflement ou de la douleur - Contrôle en {SPECIALTY} sous 14 jours - Mesurer la tension sur les deux bras lors du prochain contrôle – {DX_NUMERIC} Examens techniques : ---------------------- - IPS mesuré : gauche 0,63, droite 0,59 - IPS post-effort : gauche 0,48, droite 0,51 - Duplex {DX_ANATOMY} : sténose significative de l'a. iliaque commune gauche - CT-angiographie abdomen/pelvis : occlusion de l'a. iliaque externe gauche, collatérales visibles - Oxymétrie du pied : TcPO2 gauche 22 mmHg, droite 28 mmHg ({DX_NUMERIC})

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:04
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
    "CRITICAL FIX (source-corpus bug, not a translation choice): the Dutch original has a literal frozen first name 'Pieter' hardcoded in narrative prose ('Pieter zegt dat hij...'), present in all 93 real training documents for this template REGARDLESS of the actual sampled NAME_PATIENT -- confirmed via direct check against train.jsonl. This is an unlabeled real-name leak in the shipped nl model's training data. Replaced with {NAME_RELATIVE} in the French version (same slot already used elsewhere in this template) rather than reproduced.",
    "Rule 4 applied: dropped 'de heer' from 'zijn de heer verliest zelden grip' -- rephrased as '{NAME_RELATIVE} garde rarement le controle de la situation' (repeats the name instead of inventing a gendered pronoun for the relative, since RELATIVE_RELATION's gender is independent of any fixed pronoun choice).",
    "v3 rework: DIAGNOSIS now properly slotted (was frozen thrice in v1).",
]},

{
"template_hash": "3e24fd05c395c508", "letter_type": "verslag technisch onderzoek", "specialty": "Urologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Antécédents ----------------- 05/2022 : {DIAGNOSIS} {DX_EPONYM} ! Cystite récidivante, {DX_ABBREV} {DX_DRUG} Effets secondaires sous {DX_DRUG_2} Antécédents familiaux -------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : cancer de la prostate à 68 ans Allergies ------ Pas d'allergie connue Traitement à l'admission ------------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h - Paracétamol 1g, 4/j, prn Anamnèse -------- Orientation {DX_ABBREV} troubles mictionnels persistants. Symptômes persistants depuis {DATE_HISTORY}. Sensation de vidange incomplète, {DX_ABBREV}. {DX_TEST}. Pas d'hématurie rapportée. Pas de pyurie. {PRONOUN_SUBJ} utilise {DX_ABBREV} depuis 3 mois, sans impact clair. {DX_NUMERIC} au contrôle. Pas d'énurésie nocturne. Examen clinique ------------------ Abdomen : {DX_ABBREV}. Pas de douleur à la percussion {DX_ANATOMY}. Toucher rectal : prostate non augmentée, non douloureuse. {DX_HOMOGRAPH}. Région génitale : {DX_ABBREV} Conclusion ------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, {DX_ABBREV} infections urinaires persistantes et urgenturie. {PRONOUN_SUBJ} présente des symptômes {DX_ABBREV} {DIAGNOSIS}, réponse insuffisante au traitement de première ligne. {DX_CODESWITCH} initié. --> Évaluation urologique complémentaire incluant débitmétrie et résidu post-mictionnel. --> Concertation avec la microbiologie {DX_ABBREV} {DX_ABBREV}. Examens techniques ---------------------- | Test | Résultat | |--------------------------|---------------| | Sédiment urinaire | {DX_NUMERIC} | | Culture urinaire | {DX_CODESWITCH} | | PSA | 3,4 µg/l | | Échographie abdominale | Pas d'hydronéphrose | | Débitmétrie | Qmax 9 ml/s ! |

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

    Validation : {DATE_VALIDATION} 15:52
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "'Dreum:' (garbled Dutch, likely a mangled digital-rectal-exam abbreviation given the surrounding prostate-exam content) rendered contextually as 'Toucher rectal :'.",
]},

{
"template_hash": "41bc0a038480dd9e", "letter_type": "ontslagbrief", "specialty": "Endocrinologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Motif d'admission ---------------- Fatigue croissante et prise de poids, suspicion de {DIAGNOSIS} ! Antécédents ---------------- 05/2020 : {DIAGNOSIS} {DX_EPONYM} ! Thyroïdite de Hashimoto {DX_ABBREV} diabète de type 2 {DX_ABBREV} {DX_CODESWITCH} Antécédents familiaux --------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : hypothyroïdie à 55 ans Allergies -------- Pas d'allergie connue Traitement à l'admission ------------------- - {DX_DRUG}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 50 µg, {DX_NUMERIC}, {DX_NUMERIC} - Paracétamol 1g, {DX_NUMERIC}, p.r.n. - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} Anamnèse -------- {HONORIFIC} {NAME_PATIENT} se présente avec une fatigue, une intolérance au froid et une sécheresse cutanée. ATCD traité pour hypothyroïdie depuis 2020. Pas de nouvelle médication. Pas de changement de poids récent. Pas de symptôme de myopathie. Pas d'irritabilité ni d'insomnie. Examen clinique ------------------- Général : patient {AGE_ADJ} de morphologie normale, pas de cyanose. Pouls : 58 battements/min, régulier Tension : 110/70 mmHg Peau : sèche, froide. Pas d'œdème périorbitaire. {DX_ANATOMY} : non hypertrophié, non douloureux à la palpation. {DX_TEST} : TSH élevée à {DX_NUMERIC}, fT4 abaissée. Évolution ------- Stabilisé pendant l'hospitalisation sous ajustement de {DX_DRUG_2}. Fatigue légèrement diminuée. Pas de plainte de dyspnée ou d'œdème. Plus de ralentissement mental rapporté. Pas d'hypoglycémie. {DX_HOMOGRAPH} stable. Surveillance continue de {DX_NUMERIC} en {SPECIALTY} {DX_ABBREV} {DIAGNOSIS}. Médication de sortie -------------- - {DX_DRUG_2}, 75 µg, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - Paracétamol 1g, {DX_NUMERIC}, p.r.n. - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} Aucun traitement à domicile enregistré Conclusion ------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. À retenir : {PRONOUN_SUBJ} présente des symptômes persistants d'hypothyroïdie, malgré {DX_DRUG_2} à la dose actuelle. Le bilan confirme {DIAGNOSIS} avec augmentation récente de {DX_NUMERIC}. La fatigue continue d'avoir un impact sur les AVQ. Aucune autre cause endocrinologique trouvée. --> Ajuster {DX_DRUG_2} jusqu'à 75 µg/j. Suivi en {SPECIALTY} dans 6 semaines pour contrôle TSH et fT4 ({DX_TEST}). --> Orienter vers une consultation diététique {DX_ABBREV} {DX_ABBREV} {DIAGNOSIS}. --> {TELEFOON} en cas de symptômes inquiétants, surtout myopathie ou troubles cardiaques.

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

    Validation : {DATE_VALIDATION} 09:23
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "'zijn vermoeidheid blijft impact hebben' (PRONOUN_POSS, not modeled) -> 'La fatigue continue d'avoir un impact' (dropped possessive, definite article suffices).",
    "'Doorverwijzen naar dietist' -> 'Orienter vers une consultation dietetique' (invariant noun phrase instead of gendered profession noun 'dieteticien(ne)').",
]},

{
"template_hash": "4a3c7855d5e742d5", "letter_type": "ontslagbrief", "specialty": "Reumatologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. Motif d'admission ---------------- {DIAGNOSIS} avec arthrose progressive touchant plusieurs articulations ! Fièvre sans foyer, investiguée {DX_ABBREV} possible {DIAGNOSIS} Antécédents ---------------- 05/2018 : {DIAGNOSIS} {DATE_HISTORY} : début des plaintes arthrologiques, {DX_DRUG} instauré {DX_ABBREV} le {DOB} Antécédents familiaux ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_HOMOGRAPH} à 58 ans {DX_ABBREV} diabète de type 2 Anamnèse psychiatrique : légers symptômes dépressifs, suivi par {NAME_RELATIVE} Allergies ------- Pas d'allergie connue Traitement à domicile ------------ Aucun traitement à domicile enregistré Traitement à l'admission ------------------- - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 50 mg, iv, {DX_NUMERIC}, {DX_ABBREV} {DX_TEST} - Paracétamol, 1 g, 4/j, prn fièvre ou douleur Anamnèse -------- {PRONOUN_SUBJ} signale depuis {DX_NUMERIC} semaines une raideur croissante des articulations interphalangiennes proximales, surtout le matin. Dure > 60 min. Pas de poussée de symptômes lupiques, pas de rash, pas de néphrite. Pas de dyspnée ni de douleur thoracique. ATCD embolie pulmonaire en 2019, {DX_CODESWITCH} Contact au {TELEFOON} pour suivi ultérieur Examen clinique ------------------ {DX_ANATOMY} : gonflement et chaleur aux MCP II-IV droites, douleur à la pression + Pas d'hypertrophie synoviale aux genoux ou chevilles Pulmonaire : {DX_ABBREV}, pas de crépitants Cardiaque : régulier, pas de souffle Peau : pas d'ulcère, pas de vascularite ! {DX_TEST} : CRP élevée à {DX_NUMERIC} mg/L, VS 45 mm/H Paraclinique ------------- Hb 11,2 g/dL, VGM 86 fL, plaquettes 410 x10⁹/L Créatinine 78 µmol/L, DFGe 76 mL/min ASAT 28 U/L, ALAT 31 U/L AAN : négatif, anti-CCP : positif (180 U), FR : faiblement positif Radiographie mains : {DIAGNOSIS} périarticulaire, érosions débutantes aux MCP Évolution -------- Traité initialement par {DX_DRUG_2} iv en thérapie relais {DX_ABBREV} {DX_NUMERIC} jours de fièvre persistante. Réponse rapide au traitement, afébrile après 4{DX_NUMERIC}. Passage à {DX_DRUG_2} oral comme DMARD, concertation avec la pharmacie {DX_ABBREV} {DX_CODESWITCH} Kinésithérapie : mobilité {DX_ABBREV} déjà entamée, bonne motivation Médication de sortie ---------------- - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} - Folate, 5 mg, {DX_NUMERIC}, {DX_ABBREV} - Paracétamol, 1 g, 4/j, prn - {DX_DRUG_2}, 25 mg, {DX_NUMERIC}, {DX_NUMERIC} (dégression selon schéma) Conclusion -------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. À retenir : les symptômes correspondent à une {DIAGNOSIS} active, avec sérologie positive et signes radiologiques de maladie érosive. Plus de signe d'atteinte organique ou d'infection à la sortie. Absence de {DIAGNOSIS} confirmée par {DX_TEST} et la clinique --> Retour à domicile avec traitement DMARD oral --> Suivi en polyclinique {SPECIALTY} dans 6 semaines {DX_ABBREV} {DX_ABBREV} --> Orienter vers une biothérapie en cas de réponse insuffisante après 3 mois --> Information transmise à {NAME_RELATIVE} au {TELEFOON} ; rendez-vous annulé constaté le {DATE_HISTORY}

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 10:06
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted (this template had the most extra fields recovered: 49).",
    "Rule 4 applied: dropped 'de heer' from 'gevolgd door de heer {NAME_RELATIVE}' -> 'suivi par {NAME_RELATIVE}'.",
    "'zijn klachten passen bij' (PRONOUN_POSS) -> 'les symptomes correspondent a' (dropped possessive).",
    "'{DIAGNOSIS} uitgesloten' bracket trap ('exclu(e)') -> 'Absence de {DIAGNOSIS} confirmee' (invariant noun 'absence' as grammatical subject).",
    "'{NAME_RELATIVE} geinformeerd' bracket trap ('informe(e)') -> 'Information transmise a {NAME_RELATIVE}' (reuses the already-validated 'Information transmise' fix pattern from this project's earlier review).",
]},
]

def main():
    out_path = "translated_templates_fr_v3.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
