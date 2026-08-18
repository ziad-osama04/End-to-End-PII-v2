# -*- coding: utf-8 -*-
"""Batch 4: 6 more templates, including the {DATE_ENCOUNTER + 8W} bug fix."""
import json

TEMPLATES = [
{
"template_hash": "87a289529c8aaff9", "letter_type": "", "specialty": "",
"masked_text_fr": """COURRIER
PATIENT : RESPONSABLE : DATE :
{NAME_PATIENT} {NAME_RESPONSIBLE} {DATE_ENCOUNTER} 02:00
INSZ{INSZ} RIZIV{RIZIV} ENVOYÉ PAR
:
{NAME_DOCTOR_SENDER}
Contenu du rapport
{ORGANIZATION}
{SPECIALTY}
Cher confrère
UNITÉ : 60418 DATE : {DATE_HISTORY}ORIGINE : caucasienne
ÂGE : {AGE}
TAILLE : 174,0 cm P O I DS : 63,0 kg I M C : 20.808
TABAGISME : non connu
SPIROMÉTRIE P r é -Broncho Ventolin
AVEC BRONCHOD. P r éd. Mes. %Préd. zScore M es. %Préd. %Chg
zScore
------------- - - - -- ----- ------ ------ - ---- ------ ----
------
CVF (L) 3.65 3.86 1 0 6 0.34 3.77 1 0 3 - 2
0.19
VEMS (L) 2.73 2.46 90-0.532.63 9 6 7
-0.19
VEMS/CVF (%) 73.17 6 3.69 87-1.3269.84 9 5 8
-0.46
DEP ( L / sec) 7.48 6.15 82-1.107.50 1 0 0 2 2
0.02
DEM 25% (L/sec) 6.77 4.90 72-1.105.87 8 7 2 0
-0.52
DEM 50% (L/sec) 3.83 1.67 44-1.642.45 6 4 4 7
-1.04
DEM 75% (L/sec) 1.17 0.42 36-0.970.52 4 4 2 4
-0.83
DEM25-75%(L/sec) 2.72 1.19 44-1.481.59 5 8 3 4 -1.09
DIM 50% (L/sec) 2 . 6 2 2 . 4 4 - 7
saisi le : {DATE_HISTORY} 08:53
RÉSISTANCE DES VOIES AÉRIENNES
BOX Préd . M e s. % Préd. z Score
----------------- - - --- - ---- - ----- - -----
Raw ( k Pa/L/s) 0 . 30 0.17 5 7
sGaw (1/(kPa*s)) 0 . 85 1.11 1 3 1
saisi le : {DATE_HISTORY} 08:53
PLÉTHYSMO. VOL. PULM. Préd. M es. %Préd. zScore
------------------- ----- - ---- ------ ------
CV (L) 3 . 7 8 3.82 1 0 1 0.06
VR ( Pleth) (L) 2 . 77 3.10 1 1 2 0.82
VGT (Pleth) (L) 3 . 68 {DX_NUMERIC} 1 35 2.11
CPT (Pleth) (L) 6 . 82 6.92 1 0 1 0.13
VR/CPT (%) 4 4.38 4 4.85 1 0 1 0.09
saisi le : {DATE_HISTORY} 08:53
TEST DE TRANSFERT Jaeger P r éd. M es. %Préd. zScore
---------------------- - ---- - ---- - ---- ------
TLco ( m mol/min/Kpa) 8.15 6.71 82-1.03Kco ( m mol/min/kPa/L) 1.20 1.03 86-0.69HB (g / d l)
TLco cHB (mmol/min/Kpa) 8.80
Kco cHB(mmol/min/kPa/L) 1.28
Va SB (L) 6 . 6 7 6.52 9 8
saisi le : {DATE_HISTORY} 08:53
Pour le calcul des valeurs de référence, celles-ci n'ont pas été extrapolées
au-delà de 70 ans.
Les valeurs significativement anormales sont indiquées par *
REMARQUE DU TECHNICIEN
-------------------
spo2 : 94%
{DX_NUMERIC} {DX_NUMERIC}
Bien confraternellement Cordialement, également au nom de
{NAME_DOCTOR} {NAME_DOCTOR_2}
{NAME_DOCTOR_3}
{NAME_DOCTOR_4}
{NAME_DOCTOR_5}
{NAME_DOCTOR}
Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
{DATE_VALIDATION}
Validation : {DATE_VALIDATION} 10:37
---------------------------------------------------------------------------
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "Pure technical spirometry/plethysmography table (extra=4, near-zero narrative content, minimal gender/agreement risk). Column headers translated (FVC->CVF, FEV1->VEMS, PEF->DEP, FEF->DEM, RV->VR, TLC->CPT, VC->CV) matching real French pulmonology convention; numeric data and OCR-style spacing noise preserved as-is to keep the same table-layout realism as the Dutch source.",
]},

{
"template_hash": "87d7ea56a0b77168", "letter_type": "spoedverslag", "specialty": "Geriatrie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                     {NAME_RESPONSIBLE}           {DATE_ENCOUNTER} 02:00
INSZ{INSZ}          RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère,

    Nous avons vu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}.

    Antécédents :
    ------------------
    {DATE_HISTORY} : {DIAGNOSIS} 03/2021 : {DX_EPONYM}, statut
    post hospitalisation {DX_ABBREV} chute 2018 : {DX_ABBREV} diabète de type 2 ! Insuffisance
    rénale chronique (DFG ~{DX_NUMERIC}) Épisodes dépressifs

    Antécédents familiaux :
    ---------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : infarctus du myocarde à 72 ans ATCD {DX_ABBREV} chez
    le père

    Allergies :
    -------
    Pas d'allergie connue

    Traitement à l'admission :
    --------------------
    - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Paracétamol 1g, 3/j, prn
    - {DX_HOMOGRAPH}, {DX_NUMERIC}, {DX_NUMERIC}, le soir

    Anamnèse :
    ---------
    Plaintes d'incontinence fécale, depuis {DATE_HISTORY}. Vertiges au
    passage en position debout depuis {DATE_HISTORY}, surtout le matin. Pas de syncope rapportée, mais
    démarche instable. La famille {DX_ABBREV} {TELEFOON} signale des chutes de plus en plus
    fréquentes, jusqu'à {DX_NUMERIC}/mois. Chute sans perte de connaissance. Parfois
    des oublis, difficulté à mémoriser de nouvelles informations. ATCD {DX_TEST}
    en 2020 sans explication associée. Cette situation entrave les tâches ménagères et
    la vie autonome.

    Examen clinique :
    -------------------
    TA 138/82 mmHg en position couchée, 116/74 mmHg debout ! orthostatisme Pouls : 78 bpm,
    régulier {DX_ANATOMY} : {DX_ABBREV}, pas de signe de localisation Motricité : test de la marche
    ralenti >12 sec ! Cognitif : MMSE {DX_NUMERIC}/30, capacité de
    concentration diminuée, désorientation temporelle Démarche : instable, petits pas,
    traînante, {DX_ABBREV} composante extrapyramidale

    CONCLUSION :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir :

    --> Poursuite de la diminution de {DX_DRUG_2} prévue {DX_ABBREV} suspicion de
    vertiges liés à la médication
    --> Initiation d'un parcours de rééducation en prévention des chutes avec kinésithérapie (voir
    rapport {DX_CODESWITCH})
    --> Évaluation multidisciplinaire de la fonction cognitive : orientation vers un
    neuropsychologue {DX_DRUG_2}
    --> Évaluation du domicile pour les risques de chute via le service social
    --> Concertation de suivi avec {NAME_RELATIVE} par téléphone le {DATE_ENCOUNTER}

    Examens techniques :
    -----------------------
    ECG : rythme sinusal, allongement PQ, pas de modification du segment ST Échographie
    {DX_ANATOMY} : {DX_ABBREV} CT-cérébral ({DATE_HISTORY}) : atrophie corticale grade
    II, leucoaraïose périventriculaire Labo : Na+ 139 mmol/L, K+ 4,1 mmol/L, urée
    {DX_NUMERIC}, créatinine élevée, DFGe 48 ml/min/1,73m²

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:32
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 4 applied: dropped 'de heer' before {NAME_RELATIVE} ('Controleoverleg met de heer {NAME_RELATIVE}').",
    "'zijn toestand belemmert' / 'zijn cognitieve functie' (PRONOUN_POSS x2) -> dropped possessive both times ('Cette situation entrave...', 'de la fonction cognitive').",
    "MINOR SOURCE BUG FOUND: Dutch original has 'CT-hersenen (DD-MM-{DATE_HISTORY})' -- a literal 'DD-MM-' format-hint prefix glued directly onto a real placeholder (a milder variant of the already-known DD-MM-YYYY leak bug that the existing LEAK_RE filter didn't catch since it lacks the literal 'YYYY'). Fixed by dropping the redundant prefix -> 'CT-cerebral ({DATE_HISTORY})'. Worth hardening prep_data_fr.py's leak regex to also flag bare 'DD-MM-'/'JJ-MM-' immediately before a placeholder.",
]},

{
"template_hash": "8dcd5d1523aac833", "letter_type": "spoedverslag", "specialty": "Vaatheelkunde",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Motif de consultation : ---------- {PRONOUN_SUBJ} signale une douleur soudaine à la jambe droite depuis {DATE_HISTORY}. Orientation depuis les urgences en lien avec suspicion de {DIAGNOSIS}. ATCD {DX_ABBREV}, {DX_ABBREV} diabète de type 2, {DX_EPONYM} (père : {NAME_RELATIVE}). Pas d'allergie connue. ! Claudication intermittente à droite depuis ±3 mois, désormais aggravée en claudication douloureuse après 50 m de marche. Aggravation {DX_ABBREV} la semaine dernière avec douleur de repos au pied droit la nuit. Médication actuelle : ---------------- - {DX_DRUG} (comp. 75 mg), 75 mg, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2} (sol 5 mg/ml), 10 mg, {DX_NUMERIC}, {DX_NUMERIC}+20h - Metformine (comp. 850 mg), 850 mg, 3/j, {DX_NUMERIC}/{DX_NUMERIC}/20h - Simvastatine (comp. 40 mg), 40 mg, {DX_NUMERIC}, {DX_NUMERIC} Aucun traitement à domicile enregistré pour symptômes vasculaires. État : ------- {PATIENT_NOUN_MARKED} {AGE_ADJ}, alerte, hémodynamiquement stable (TA 140/90 mmHg). Pas d'ictère, de cyanose, de difficulté respiratoire. Contact téléphonique avec {NAME_RELATIVE} ({TELEFOON}) : confirme les symptômes initiaux. Examen clinique : ------------------- Pouls jambe droite : {DX_ABBREV} a. fémorale distale, ! aucune pulsation palpable au niveau de a. dorsale du pied et a. tibiale postérieure. Jambe gauche : pouls normaux. Température du pied droit plus basse qu'à gauche, ! décoloration bleuâtre des 2e et 3e orteils droits. Remplissage capillaire > 5 sec à droite, < 2 sec à gauche. Motricité et sensibilité globalement intactes, léger déficit en flexion dorsale du pied droit. {DX_TEST} : test de Buerger négatif à gauche, positif à droite. {DX_HOMOGRAPH} : peau froide, pâle avec livedo débutant. Examen technique : -------------------- Duplex {DX_ANATOMY} : sténose critique de l'a. fémorale commune droite proximale (90 %), occlusion de l'a. poplitée droite. {DX_NUMERIC} : Hb 8,4 g/dL, CRP 45 mg/L, D-dimères ↑↑. CT-angiographie planifiée dans les 24h {DX_ABBREV} ischémie aiguë menaçant le membre. Conclusion : -------- Le {PATIENT_NOUN_GENERIC} a été vu {DX_ABBREV} ischémie artérielle aiguë du membre inférieur droit, étiologie possiblement embolique. --> Intervention immédiate nécessaire : consultation en urgence de chirurgie vasculaire {SPECIALTY}. --> Anticoagulation débutée : {DX_CODESWITCH} 1500 UI/h iv. --> Orientation vers le bloc opératoire après confirmation CT. --> Nous contacter en cas de progression vers une ischémie complète ou d'aggravation de la douleur. Le {PATIENT_NOUN_GENERIC} susmentionné est actuellement surveillé aux urgences.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:20
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
    "Rule 5 applied: bare 'patient werd gezien' (no article) and 'Bovengenoemde wordt bewaakt' -> both '{PATIENT_NOUN_GENERIC}' + invariant subject.",
]},

{
"template_hash": "910ee8bd5e921c1b", "letter_type": "spoedverslag", "specialty": "Gastro-enterologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation de gastro-entérologie le {DATE_ENCOUNTER}. Motif de consultation : ---------- {DATE_HISTORY} : {DIAGNOSIS} 03/2023 : {DX_EPONYM} ! {DX_ABBREV} diabète sucré antécédents familiaux : {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_HOMOGRAPH} à l'âge de 68 ans Allergies : ------- Pas d'allergie connue Traitement à l'admission : -------------------- - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 500 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h - paracétamol (comp. 1000 mg), 1 comp, 3/j, prn douleur Aucun traitement à domicile enregistré {DX_ABBREV} discontinué depuis {DATE_HISTORY} Anamnèse : --------- Orientation par le médecin généraliste {DX_ABBREV} douleurs abdominales persistantes depuis {DATE_HISTORY}. {PRONOUN_SUBJ} rapporte une douleur colique en fosse iliaque droite, intermittente, ! depuis quelques semaines également un léger changement du transit : constipation de plus en plus fréquente suivie de selles molles. Pas de perte de poids rapportée. Pas de plainte nocturne. ATCD appendicectomie à 22 ans. {DX_ABBREV} Examen clinique : ------------------- état général : {AGE_ADJ} en bonne condition abdomen : souple, péristaltisme {DX_ABBREV}, douloureux en fosse iliaque droite !, pas de défense {DX_TEST} : négatif pour le sang dans les selles {DX_ANATOMY} : pas de masse palpable {DX_ABBREV} CRP et leucocytose normales aux urgences Examen technique : -------------------- Écho abdominale : pas de dilatation intestinale, pas d'anomalie hépatobiliaire CT-abdomen (avec contraste) : iléite terminale évoquant une maladie de Crohn {DX_CODESWITCH}, pas d'abcès ni de fistule. Confirmé par coloscopie avec biopsies : {DIAGNOSIS} Conclusion : -------- Le {PATIENT_NOUN_GENERIC} susmentionné a été vu le {DATE_ENCOUNTER}. --> diagnostic : {DIAGNOSIS} avec iléite active. --> instauration de {DX_DRUG_2}, {DX_NUMERIC}, 9h, évaluation dans 8 semaines. --> suivi en polyclinique {SPECIALTY}, contrôle dans 8 semaines. Contactez-nous en cas d'aggravation ou de nouveau saignement. {TELEFOON}

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

    Validation : {DATE_VALIDATION} 16:42
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "MAJOR SOURCE BUG FIX: the Dutch original has a literal, never-rendered '{DATE_ENCOUNTER + 8W}' placeholder baked into all 93 real training documents for this template (render()'s regex can't match spaces/operators inside braces, so this leaked through as raw unrendered text into the shipped nl model's training data -- confirmed by direct check against train.jsonl). Replaced with the natural relative-time phrase 'contrôle dans 8 semaines' instead of reproducing the bug.",
    "Like 7fed825dd1a65d86, this template hardcodes literal 'gastro-enterologie' in one spot alongside a genuine {SPECIALTY} slot later -- kept both, matching source structure.",
]},

{
"template_hash": "9a50599674086393", "letter_type": "consultatiebrief", "specialty": "Geriatrie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. Anamnèse : --------- {PRONOUN_SUBJ} se présente avec {DIAGNOSIS}, progressif depuis {DX_NUMERIC}/2023. Par ailleurs plaintes de vertiges au lever, sans syncope. ATCD {DX_ABBREV}, {DX_ABBREV} diabète de type 2. {DX_EPONYM} absent dans la famille, mais {RELATIVE_RELATION} : {NAME_RELATIVE} a {DX_HOMOGRAPH}. Pas de plainte cognitive rapportée par {NAME_RELATIVE} ; {PRONOUN_SUBJ} vit en solitaire. Pas de problème d'AVQ, mais AIVQ partiellement limitées {DX_ABBREV} motivation. ! plaintes de fatigue depuis 06/2024, rapportées via {TELEFOON}. Médication actuelle : ------------------ - {DX_DRUG} (comp. 5 mg), 5 mg, {DX_NUMERIC}, 9h - Metformine (comp. 850 mg), 850 mg, {DX_NUMERIC}, 9h et 21h - {DX_DRUG_2} (solution 10 mg/ml), 10 mg, {DX_NUMERIC}, 10h - Acide acétylsalicylique (comp. 75 mg), 75 mg, {DX_NUMERIC}, {DX_NUMERIC} Pas d'allergie connue Examens techniques : -------------------------- Hb 8,2 g/dL ({DX_TEST}), ferritine 18 µg/L, TSH 5,6 mU/L. Vitamine B12 et acide folique {DX_ABBREV}. ECG : rythme sinusal, pas d'anomalie pertinente. {DX_ANATOMY} : pas d'œdème, pas de démarche instable. MMSE : 24/30, en lien avec {DX_CODESWITCH} dans les antécédents. Conclusion : -------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} {DIAGNOSIS} et fatigue persistante. Anémie constatée, possiblement multifactorielle (maladie chronique + {DX_HOMOGRAPH}). ! Fonctionnellement intact, mais isolement social comme facteur de risque. Le {PATIENT_NOUN_GENERIC} susmentionné a pour date de naissance {DOB}. --> Instauration de fer par voie orale après concertation avec {DX_DRUG_2}. --> Répéter le bilan sanguin dans 6 semaines : Hb, ferritine, CRP. --> Orienter vers le service social {DX_ABBREV} évaluation du réseau social. Conseils : ------- Nous contacter en cas d'aggravation de l'état général ou de nouveaux symptômes. {PRONOUN_SUBJ} peut poursuivre la médication actuelle, aucun ajustement requis. Aucun traitement à domicile enregistré en dehors de la liste ci-dessus. Examens techniques : ------------------------ IRM colonne vertébrale : {DX_DRUG_2} au niveau {DX_ANATOMY}, pas de compression à {DX_NUMERIC} niveau. Échocardiographie : légère hypertrophie VG, FE 55 %, {DX_CODESWITCH} exclu. Test DX réalisé le {DATE_HISTORY} : {DX_TEST}, résultat stable par rapport au précédent.

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

    Validation : {DATE_VALIDATION} 15:29
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'hij woont alleen' -> '{PRONOUN_SUBJ} vit en solitaire' (invariant, reuses the established fix).",
    "'Bovengenoemde patient heeft X als geboortedatum' -> 'Le {PATIENT_NOUN_GENERIC} susmentionne a pour date de naissance X' (invariant subject).",
]},

{
"template_hash": "9d473e296bb4bd5c", "letter_type": "ontslagbrief", "specialty": "Dermatologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                  {NAME_RESPONSIBLE}                   {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

 Le {PATIENT_NOUN_GENERIC} susmentionné a été vu au service de {SPECIALTY} le {DATE_ENCOUNTER}. Motif de consultation : ----------- {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM} ! Co diabète sucré et hypertension ATCD {DX_ABBREV} {DX_ABBREV} lésions cutanées aux deux jambes Antécédents familiaux : ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à 70 ans Allergies : ---------- Pas d'allergie connue Traitement à domicile : -------------- Aucun traitement à domicile enregistré Traitement à l'admission : ------------------ - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, 10h - Pommade X (tubes 5 %), {DX_NUMERIC}, le soir - {DX_DRUG_2}, 1 suppo, {DX_NUMERIC}, le soir Anamnèse : --------- Orientation par le médecin traitant {DX_ABBREV} lésions persistantes et prurigineuses au niveau {DX_ANATOMY}. Symptômes présents depuis ±6 mois. Aggravation progressive malgré des antifongiques locaux. Le {PATIENT_NOUN_GENERIC} a utilisé {DX_DRUG_2} de sa propre initiative, sans effet. La peau est depuis plus sèche et rouge. Pas de fièvre, pas de perte de poids. Pas de voyage récent ni de {DX_CODESWITCH}. État : ------- {HONORIFIC} {NAME_PATIENT}, {AGE_ADJ}, {DOB}. Admission le {DATE_ENCOUNTER} à la demande du service {SPECIALTY} {DX_ABBREV} altérations cutanées anormales. Pas d'ictère, pas de lymphadénopathie. Température : 37,1 °C. Examen clinique : ------------------- {DX_ANATOMY} : érythème, desquamation et fissures dans le pli interfessier, accentué à droite. ! Les deux jambes : xérose, légère hyperpigmentation, peau atrophique. Pas d'ulcère actif, pas d'exsudation. Pas d'induration sous-cutanée. {DX_ABBREV} {DX_HOMOGRAPH}. Trop : {DX_TEST} Réflexes : {DX_NUMERIC}/4 à gauche, {DX_NUMERIC}/4 à droite Examen technique : -------------------- - Préparation KOH : positive pour hyphes - Cultures : résultat en attente {DX_CODESWITCH} - Biopsie {DX_ANATOMY} : en cours, résultat ultérieur - CRP : 8 mg/L (n) - GDS : {DX_ABBREV} - {DX_TEST} : saturation périphérique normale Conclusion : -------- Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} signale des démangeaisons et douleurs persistantes dans le pli interfessier, aggravées sous {DX_DRUG_2}. Depuis l'utilisation de {DX_DRUG_2}, légère amélioration, mais lésions toujours actives. ! Tableau anamnestique et clinique compatible avec {DIAGNOSIS}, possiblement secondaire à {DX_NUMERIC} ou {DX_ABBREV}. Une contribution de dermatite de contact via {DX_HOMOGRAPH} n'est pas exclue. --> Arrêt de {DX_DRUG_2} {DX_ABBREV} effet potentiellement irritant. --> Instauration de {DX_DRUG_2} ({DX_NUMERIC}) + pommade à l'hydrocortisone ({DX_NUMERIC}) temp. 14 jours --> Orienter vers une consultation diététique {DX_ABBREV} {DX_NUMERIC} et gestion du poids --> Consultation podologie {DX_ABBREV} soin des pieds {DX_ABBREV} diabète --> Contrôle en {SPECIALTY} dans 6 semaines, en attendant la biopsie Remarque : ---------- Le {PATIENT_NOUN_GENERIC} a été informé de l'importance de l'hygiène et de l'hydratation. {PRONOUN_SUBJ} a compris les conseils et appellera le {TELEFOON} en cas d'aggravation.

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

    Validation : {DATE_VALIDATION} 15:11
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'zij werd door huisarts verwezen' (gendered-participle trap) -> 'Orientation par le medecin traitant ...' (noun-based).",
    "'haar huid is sindsdien droger' (PRONOUN_POSS) -> 'La peau est depuis plus seche' (dropped possessive).",
    "'Patiënt gebruikte X' / 'Patiënt geïnformeerd' (bare mentions) -> {PATIENT_NOUN_GENERIC} per Rule 5.",
]},
]

def main():
    out_path = "translated_templates_fr_batch4.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
