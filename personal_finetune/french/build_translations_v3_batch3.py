# -*- coding: utf-8 -*-
"""Batch 3 of the v3-based French template translation: 6 more templates."""
import json

TEMPLATES = [
{
"template_hash": "72d66c0dd0e910a7", "letter_type": "spoedverslag", "specialty": "Dermatologie",
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

    Antécédents
    ----------------
    {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM} ! Co dermatite
    atopique ATCD {DX_ABBREV}, sans exacerbation récente Problématique psychiatrique
    (symptômes dépressifs)

    Antécédents familiaux
    ---------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à 45 ans
    {RELATIVE_RELATION} : psoriasis, diagnostiqué à 20 ans

    Allergies
    --------
    Pas d'allergie connue ! Réaction signalée à {DX_DRUG} (éruption,
    rétention hydrique)

    Traitement à domicile
    --------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - Paracétamol 1g, 3/j, si besoin
    - {DX_DRUG_2}, crème, local, {DX_NUMERIC}
    Aucun traitement à domicile enregistré {DX_ABBREV} vitamines

    Anamnèse
    ---------
    Orientation par le médecin traitant {DX_ABBREV} exanthème progressif depuis {DATE_HISTORY}. {PRONOUN_SUBJ} signale
    des démangeaisons ! qui s'aggravent le soir et la nuit. Pas de voyage récent
    ({DX_CODESWITCH}), pas de contact avec des malades. Symptômes initiaux
    débutés comme un érythème sur {DX_ANATOMY}, s'étendant au torse et aux membres
    proximaux. Pas de pyrexie, pas de plainte respiratoire. Co diabète de type 2,
    contrôlé. Fièvre intermittente la semaine précédant la présentation, {DX_ABBREV}
    source infectieuse. Pas d'utilisation récente de nouveaux cosmétiques ou produits.

    Examen clinique
    -----------------
    Général : {AGE_ADJ}. Conscience normale, orientation normale. Peau : exanthème
    maculopapuleux symétrique sur le tronc, les cuisses, les bras proximaux. Lésions
    confluentes, certaines avec {DX_HOMOGRAPH} central. Nikolsky -, {DX_ABBREV}
    muqueuse. {DX_ANATOMY} : érythème à bords finement squameux, ! prurit.
    Pas de vésiculation. Flexion cervicale : négatif {DX_ABBREV} méningisme. Temp : 37,8 °C
    ({DX_NUMERIC}) CRP : ↑ {DX_NUMERIC} mg/L Globules blancs : {DX_ABBREV}

    CONCLUSION
    -----
    Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} a été vu {DX_ABBREV} exanthème d'évolution subaiguë avec
    composante systémique. Le diagnostic différentiel comprend {DX_EPONYM},
    réaction médicamenteuse ({DX_DRUG_2} ?), ou exanthème viral
    (EBV/{DX_TEST}).
    --> Consultation {SPECIALTY} initiée.
    --> Biopsie cutanée prélevée sur lésion {DX_ANATOMY}, envoyée en anatomopathologie.
    --> Bilan sanguin répété : hémogramme complet, CRP, bilan hépatique, sérologie EBV, test VIH
    --> Arrêt temporaire de {DX_DRUG_2} {DX_ABBREV} rôle suspect dans l'éruption, en
    attendant les résultats
    --> Paracétamol en cas de fièvre ou d'inconfort, pas d'AINS administrés {DX_ABBREV} risque
    de déplacement

    Examens techniques
    ----------------------
    {DATE_ENCOUNTER} :
    - Biopsie cutanée (région lombaire) : envoyée en anatomopathologie ({DX_CODESWITCH})
    - Sang : NFS, CRP, bilan hépatique, rénal, EBV IgM/IgG, Ag/Ac VIH – résultats en attente
    - Urine : {DX_ABBREV} sédiment, pas de protéinurie
    {DX_TEST} : négatif sur écouvillon nasopharyngé (RSV/grippe) ECG :
    rythme sinusal, {DX_ABBREV} interventions {DX_NUMERIC} mmHg (tension en décubitus)

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:33
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'Algemeen: X patient, wakker, orienterend' -> 'Conscience normale, orientation normale' (reuses the already-validated 'Conscient(e)' fix from earlier project review).",
    "'De X patient werd gezien' -> 'Le {PATIENT_NOUN_GENERIC} X a ete vu' (invariant subject).",
]},

{
"template_hash": "76d1a7e25fa2b21a", "letter_type": "consultatiebrief", "specialty": "Cardiologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. Motif d'admission ---------------- Dyspnée à l'effort, symptômes depuis {DX_NUMERIC} semaines. Douleur rétrosternale de type reflux, sans irradiation. Orientation {DX_ABBREV} suspicion de {DIAGNOSIS}. Antécédents ---------------- 12-03-{DATE_HISTORY} : hypertension diagnostiquée 06/{DATE_HISTORY} : {DX_EPONYM} ! Asthme bronchique {DX_ABBREV} trouble de la fonction pulmonaire Pontage coronarien en {DOB} - statut post PAC x3 Antécédents familiaux --------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_ABBREV} à 58 ans Allergies -------- Pas d'allergie connue Traitement à l'admission ------------------- - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 5 mg, {DX_NUMERIC}, 9h - Ascal (comp. 75 mg), {DX_NUMERIC}, 10h - Nebilet (comp. 5 mg), {DX_NUMERIC}, {DX_NUMERIC} Anamnèse --------- {PRONOUN_SUBJ} signale une tolérance à l'effort réduite : essoufflement dès une activité légère (NYHA classe II). Pas d'orthopnée ni de DPN. Pas de palpitations ni de syncope. Parfois légère oppression thoracique nocturne. Pas de fièvre, pas de perte de poids. {HONORIFIC} utilise {TELEFOON} pour les contacts urgents. ATCD {DX_CODESWITCH} et facteurs de risque cardiaque : ex-fumeur, dyslipidémie. Examen clinique ----------------- TA : 138/86 mmHg, pouls 72/min régulier {DX_ANATOMY} : {DX_ABBREV}, pas d'œdème, TVJ non augmentée Auscultation thorax : bruits cardiaques réguliers, B1/B2 intacts, pas de souffle Pulmonaire : libre, sans ronchi ni sibilances {DX_TEST} : ECG normal, rythme sinusal, QRS normal Écho : FEVG 50 %, pas d'anomalie régionale de la cinétique pariétale Laboratoire : troponine négative, CRP normale, NT-proBNP légèrement élevé {DX_NUMERIC} Évolution ------ Stable pendant l'hospitalisation, pas d'aggravation des symptômes. Capacité à l'effort testée par test de marche de 6 minutes : distance {DX_NUMERIC} m, dyspnée comme seule plainte. Le suivi {DX_HOMOGRAPH} n'a montré aucune progression par rapport au scanner précédent. Résultat {DX_TEST} : négatif pour embolie pulmonaire. Médication de sortie ---------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 5 mg, {DX_NUMERIC}, 9h - Ascal (comp. 75 mg), {DX_NUMERIC}, 10h - Nebilet (comp. 5 mg), {DX_NUMERIC}, {DX_NUMERIC} - Atorvastatine (comp. 40 mg), {DX_NUMERIC}, {DX_NUMERIC} Conclusion ------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en consultation en {SPECIALTY} le {DATE_ENCOUNTER}. À retenir : statut post chirurgie cardiaque, symptômes actuels compatibles avec une limitation fonctionnelle {DX_ABBREV} {DIAGNOSIS}. Pas de signe de problème cardiaque aigu lors de l'évaluation. Les données ont été transmises au kinésithérapeute {DX_ABBREV} conseils d'entraînement. --> contrôle chez le cardiologue dans 4 mois ou plus tôt en cas d'aggravation. --> orientation vers la revalidation respiratoire {DX_ABBREV} {DX_NUMERIC}.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 08:29
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'zijn gegevens doorgestuurd' (PRONOUN_POSS, not modeled) -> 'Les donnees ont ete transmises' (dropped possessive).",
]},

{
"template_hash": "7c08af15fb5939d8", "letter_type": "spoedverslag", "specialty": "Pneumologie",
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

    UNITÉ : 40552 DATE : {DATE_ENCOUNTER} ORIGINE : noire ÂGE :
    {AGE} TAILLE 182,7 cm POIDS : 95,3 kg IMC :
    28,553 TABAGISME : non connu

    Anamnèse :
    ---------
    {DATE_HISTORY} : {DIAGNOSIS} 10/2023 : exacerbation BPCO, {DX_ABBREV}
    antibiotiques et corticoïdes 05-04-{DATE_ENCOUNTER} : début aigu de dyspnée douloureuse
    droite, {DX_ABBREV} fièvre {DX_ABBREV} Signale une toux productive depuis ±1 semaine avec
    expectorations jaune-vert, ! alarmant par fatigue respiratoire accrue. Pas d'hémoptysie, pas
    d'orthopnée, pas d'œdème périphérique. ATCD {DX_ABBREV}, statut post {DX_EPONYM}
    (2019) {DX_ABBREV} diabète de type 2, hypertension Pas de voyage récent, pas
    d'exposition à des infections connues. Décès de {NAME_RELATIVE} ({RELATIVE_RELATION}) à 72 ans,
    d'un carcinome pulmonaire.

    Médication actuelle :
    -------------------
    - {DX_DRUG}, 1 inhal/j, le matin
    - {DX_DRUG_2}, 500 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Ramipril 5 mg, {DX_NUMERIC}, {DX_NUMERIC}
    - Metformine 850 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Atorvastatine 20 mg, {DX_NUMERIC}, soir
    Aucun traitement à domicile enregistré pour analgésiques ou sédatifs

    Examens techniques :
    -------------------------
    SANG : {DX_TEST} - Hb 138, GB 14,2↑, CRP 112↑, {DX_NUMERIC}
    URÉE/CRÉAT : normal IMAGERIE : RX-thorax {DATE_ENCOUNTER} → densité S6 droite,
    légère réaction pleurale, {DX_ANATOMY} CT-thorax urgences → infiltrats
    subcentraux droits, cavitation ?, {DX_CODESWITCH} n/a Spirométrie
    ancienne : VEMS 68 % prévu, VEMS/CVF 0,61

    Conclusion :
    ------
    {PATIENT_NOUN_MARKED} {AGE_ADJ}. Orientation aux urgences de pneumologie {DX_ABBREV} aggravation des symptômes respiratoires.
    --> tableau clinique et biologique compatible avec une pneumonie droite, possible
    composante d'aspiration
    Absence de {DX_HOMOGRAPH} confirmée, pas de diminution à gauche. Pas de signe
    d'insuffisance cardiaque ou d'embolie pulmonaire à l'imagerie. Traitement initial débuté par
    {DX_DRUG_2} iv, passage à la voie orale prévu. Admission prévue en lit {SPECIALTY}.

    Conseils :
    -------
    Admission au service {SPECIALTY} pour antibiothérapie iv (ceftriaxone +
    azithromycine) selon protocole Réévaluation dans 4{DX_NUMERIC} {DX_ABBREV} réponse
    Culture d'expectorations, gazométrie dans les 6h Compléter la fiche de contact concernant le
    statut vaccinal (pneumocoque, grippe) Dépistage complémentaire des facteurs de risque
    {DX_DRUG_2} en cas de suspicion de récidive

    Examens techniques :
    -----------------------
    - RX-thorax : {DX_ANATOMY}, consolidation base droite, réaction pleurale
    - CT-thorax : consolidation segmentaire S6 droite avec bronchogramme aérien, infiltration périfocale
    - ECG : rythme sinusal 98/min, extrasystoles supraventriculaires, pas de sus-décalage ST
    - Gazométrie (air) : {DX_NUMERIC}, pO2 9,8 kPa, pCO2 5,1 kPa, HCO3 24 mmol/L

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 13:03
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 4 applied: dropped 'mevrouw' before {NAME_RELATIVE} ('mevrouw {NAME_RELATIVE} ({RELATIVE_RELATION}) overleden').",
    "'{NAME_RELATIVE} overleden' (deceased, gendered participle) -> 'Deces de {NAME_RELATIVE}' (noun-based, invariant).",
    "'X patiente werd doorverwezen' / '{DX_HOMOGRAPH} uitgesloten' / 'zij klaar voor opname' -- three separate gendered-participle traps in one paragraph -> restructured as three invariant-noun-subject sentences ('Orientation aux urgences...', 'Absence de X confirmee...', 'Admission prevue en lit X.').",
]},

{
"template_hash": "7fed825dd1a65d86", "letter_type": "", "specialty": "",
"masked_text_fr": """COURRIER
PATIENT : RESPONSABLE : DATE :
{NAME_PATIENT} {NAME_RESPONSIBLE} {DATE_ENCOUNTER} 02:00
INSZ{INSZ} RIZIV{RIZIV} ENVOYÉ PAR
:
{NAME_DOCTOR_SENDER}
Contenu du rapport
{ORGANIZATION}
{SPECIALTY}
Cher confrère,
Nous avons vu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation de
gastro-entérologie le {DATE_HISTORY}.
Antécédents :
-----------------
{DATE_HISTORY} : Épididymite gauche.
{DATE_HISTORY} : {DIAGNOSIS}
Antécédents familiaux :
----------
{RELATIVE_RELATION} (fille du frère du père) : cancer du côlon à {AGE} ans
{RELATIVE_RELATION} (côté paternel) : cancer du côlon à {AGE} ans
Allergies :
---------
Pas d'allergie connue
Traitement à l'admission :
--------------------
Aucun traitement à domicile enregistré
Anamnèse :
---------
Traitement débuté par suppositoires, avec amélioration très rapide des symptômes. Plus
de douleur à la défécation. Encore très occasionnellement un peu de sang dans les selles en cas
d'effort important, uniquement sur le papier. Plus de douleur à l'essuyage. Transit normalisé.
La kinésithérapie du plancher pelvien n'a pas été instaurée.
La fissure s'est révélée bien cicatrisée à la coloscopie.
Examens techniques :
-----------------------
* Coloscopie totale 24/04 :
CONCLUSION :
macroscopiquement {DX_ABBREV} iléo-coloscopie
biopsies pour exclure une colite microscopique
{DX_ABBREV} :
Colite chronique légère non spécifique.
CONCLUSION :
--------
Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE} ans, en consultation en {SPECIALTY} le
{DATE_HISTORY}. À retenir :
Contrôle dans le cadre de {DIAGNOSIS}, voir courrier précédent.
L'instauration initiale de pommade au Diltiazem n'a donné qu'une amélioration insuffisante. À
l'examen proctologique, un tonus sphinctérien et du plancher pelvien fortement contracté a été
observé. Finalement, avec l'instauration de {DX_DRUG} et de
{DX_DRUG_2}, disparition complète des symptômes. Le transit est
normalisé, plus de douleur à la défécation, encore sporadiquement un peu de sang sur le
papier après défécation.
La coloscopie totale s'est révélée rassurante, une guérison complète de la
fissure était déjà constatée à ce moment-là.
En cas de récidive des symptômes, la kinésithérapie du plancher pelvien semble
indiquée pour traiter {DIAGNOSIS}. Pour l'instant, poursuite d'une prise en charge conservatrice.
Les mesures hygiéniques concernant la prévention de la constipation ont été passées en revue
(posture aux toilettes, alimentation riche en fibres, hydratation, activité physique...). Laxatif
osmotique selon les besoins.
Bien confraternellement
{NAME_DOCTOR} Cordialement,
{NAME_DOCTOR_2}
Ce rapport a été validé électroniquement par {NAME_DOCTOR_2} le {DATE_VALIDATION}
Validation : {DATE_VALIDATION} 10:18
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
    "This template's meta.letter_type/specialty are blank in the recovery -- content is GI/proctology-specific with the specialty hardcoded as literal 'gastro-enterologie' text in one place (kept literal, matching source) alongside one genuine {SPECIALTY} slot later. Likely one of the five real HealthOne Nova seed letters run through the same pipeline (much lower extra-field count: 11 vs the ~30-50 typical of other templates) -- content translated faithfully rather than force-restructured.",
    "Rule 5 applied: bare 'Uw X patiente werd gezien' -> active-voice 'Nous avons revu X, {PATIENT_NOUN_MARKED} de X ans, en consultation en {SPECIALTY}...'.",
    "Extended family-relation parentheticals ('dochter van broer van vader', 'paternele zijde') translated literally as fixed text alongside the {RELATIVE_RELATION} slot, since they describe a specific relation structure beyond what any slot models.",
]},

{
"template_hash": "804ff21417432ba8", "letter_type": "ontslagbrief", "specialty": "Reumatologie",
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

    Anamnèse :
    ---------
    {DATE_HISTORY} : {DIAGNOSIS} 05/2023 : début des symptômes aux
    poignets, progressif {DX_EPONYM} ! {DX_ABBREV} arthropathie {DX_ABBREV}
    Raideur intermittente du poignet droit, surtout le matin, dure >1h
    Pas de pic fébrile, pas de perte de poids {DX_NUMERIC} jours de
    fatigue après effort minime {NAME_RELATIVE} ({RELATIVE_RELATION}) : {DX_ABBREV} dans
    les antécédents ATCD {DX_CODESWITCH} sans symptôme actif

    Médication actuelle :
    -------------------
    - {DX_DRUG}, 5mg, {DX_NUMERIC}, {DX_NUMERIC}
    - Paracétamol 1g, 3/j, prn
    - {DX_DRUG_2}, 0,5 comprimé, {DX_NUMERIC}, 20h
    Aucun traitement à domicile enregistré

    Examens techniques :
    -------------------------
    BILAN : CRP {DX_NUMERIC} mg/l, Hb 12,8 g/dl, VS élevée Facteur rhumatoïde :
    positif ({DX_TEST}) Anti-CCP : fortement positif RX mains : modifications
    érosives aux MCP II-IV, {DX_ABBREV} {DX_ANATOMY} {DX_HOMOGRAPH}
    à l'écho de l'épaule droite, synovite grade 2 IRM articulations sacro-iliaques :
    sacro-iliite active à gauche, {DX_ABBREV} {DX_DRUG_2}

    Conclusion :
    ------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} de {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir :

    {PRONOUN_SUBJ} répond aux critères de {DIAGNOSIS}. Diagnostic confirmé par la sérologie
    et l'imagerie. Symptômes depuis {DATE_HISTORY}, réponse insuffisante au
    traitement de première ligne. Pas de manifestation extra-articulaire à ce jour.

    --> start DMARD biologique : {DX_DRUG_2}, sous-cutané 50mg/semaine
    --> référence vers la kinésithérapie {DX_ABBREV} programme avec rhumatologue
    --> contrôle dans 3 mois avec répétition du bilan et évaluation DAS28

    Conseils :
    -------
    Les symptômes sont à signaler via {TELEFOON} en cas d'aggravation. Instructions données
    {DX_ABBREV} risque infectieux pendant l'immunosuppression. Statut vaccinal vérifié :
    {DX_DRUG_2} à jour Pas d'allergie connue Le {PATIENT_NOUN_GENERIC} susmentionné est
    informé de la nature et du pronostic de {DIAGNOSIS}

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:29
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
    "Rule 4 applied: dropped 'mevrouw' before {NAME_RELATIVE}.",
    "'haar klachten melden' (PRONOUN_POSS) -> 'Les symptomes sont a signaler' (dropped possessive).",
    "'{DIAGNOSIS}, bevestigd via serologie' (gendered participle trap on DIAGNOSIS) -> split into two sentences, 'Diagnostic confirme par...' (agrees with invariant masculine 'diagnostic').",
]},

{
"template_hash": "8715ed79da6d70ad", "letter_type": "opvolgbrief", "specialty": "Vaatheelkunde",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Antécédents : ----------------- {DATE_HISTORY} : {DIAGNOSIS} {DIAGNOSIS} ! Douleurs {DX_ANATOMY} depuis 6 mois {DX_ABBREV} pontage {DX_ABBREV} {DX_CODESWITCH} Antécédents familiaux : ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à 65 ans Allergies : --------- Pas d'allergie connue Anamnèse : --------- Orientation {DX_ABBREV} claudication intermittente progressive à droite. Co {DX_ABBREV}. Périmètre de marche réduit à environ 200 m. Pas de douleur de repos. Pas d'ulcère. {PRONOUN_SUBJ} utilise {DX_DRUG} depuis {DATE_HISTORY}, sans {DX_NUMERIC} amélioration. Le médecin traitant a débuté {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}. Pas d'effet secondaire rapporté. Pas de plainte d'impuissance ou d'infection urinaire. {HONORIFIC} répond de façon adéquate aux questions. Examen clinique : ------------------- Pouls : droite {DX_ABBREV}, gauche faiblement palpable TA : 140/90 mmHg {DX_ANATOMY} : atrophie à droite, pilosité augmentée à gauche Remplissage capillaire droit ralenti : 4 sec ! {DX_TEST} : négatif Neurologique : sensibilité {DX_ABBREV} aux deux jambes jusqu'aux malléoles Pas d'ulcération ni de nécrose Conclusion : -------- Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} a été évalué le {DATE_ENCOUNTER} {DX_ABBREV} claudication droite avec des constatations cliniques pathologiques. À retenir : {DX_DRUG_2} poursuivi pendant 6 mois sans réponse. {DX_HOMOGRAPH}. Plan initial {DX_ABBREV} revascularisation reconsidéré. --> {DX_TEST} (Doppler) indiqué pour établir les pressions segmentaires. --> En cas d'anomalie {DX_NUMERIC} : consultation avec {SPECIALTY} pour la suite de la stratégie. --> {TELEFOON} en cas de symptômes liés à {DX_DRUG_2}. Aucun traitement à domicile enregistré en dehors de la médication citée. Suivi rapproché dans 3 mois ou plus tôt en cas de progression.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 15:36
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
    "'zijn gevoel' (PRONOUN_POSS) -> 'sensibilite' (dropped possessive, bare noun suffices).",
]},
]

def main():
    out_path = "translated_templates_fr_batch3.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
