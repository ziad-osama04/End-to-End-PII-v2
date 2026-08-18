# -*- coding: utf-8 -*-
"""Batch 6: 6 more templates."""
import json

TEMPLATES = [
{
"template_hash": "b88f12862e51c888", "letter_type": "spoedverslag", "specialty": "Vaatheelkunde",
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

    Antécédents
    ----------------
    {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM} ! {DX_ABBREV} diabète
    {DX_ABBREV} {DX_ABBREV} {DX_ABBREV} {DX_DRUG} depuis {DATE_HISTORY}

    Antécédents familiaux
    ---------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à 55 ans

    Allergies
    --------
    Pas d'allergie connue

    Traitement à l'admission
    -------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - {DX_DRUG_2}, suppo {DX_NUMERIC}, la nuit
    - {DX_DRUG_2}, 1 crème, {DX_NUMERIC}

    Anamnèse
    --------
    Orientation {DX_ABBREV} {DX_TEST}. Symptômes persistants depuis {DATE_HISTORY}.
    {PRONOUN_SUBJ} signale une douleur au niveau {DX_ANATOMY}, s'aggravant à l'effort.
    Aggravation ces {DX_NUMERIC} dernières semaines. {DX_CODESWITCH}
    rapporté. Pas de claudication, mais sensation de lourdeur dans la jambe. Pas d'ulcère. !
    jambe douloureuse.

    Examen clinique
    -------------------
    Pouls périphériques palpables {DX_ABBREV} {DX_ANATOMY} : {DX_HOMOGRAPH},
    légère tuméfaction, douloureux à la palpation, œdème 3+ au tibia gauche Doppler :
    {DX_TEST} Remplissage capillaire >3 secondes Altérations cutanées
    au niveau du pied, pas d'ulcère Différence de température bilatérale de 2°C

    CONCLUSION
    ------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir :

    Les symptômes évoquent {DIAGNOSIS}, mais évolution progressive. !
    {DX_HOMOGRAPH} avec le tableau clinique. {DX_CODESWITCH}
    noté.

    --> {DX_NUMERIC} à reporter {DX_ABBREV} intolérance à {DX_DRUG_2}
    --> orientation vers {SPECIALTY} pour évaluation complémentaire
    --> nouvelle demande de duplex via {TELEFOON}
    --> contrôle dans {DX_NUMERIC} semaines

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:57
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'haar klachten lijnen met X' (PRONOUN_POSS) -> 'Les symptomes evoquent X' (dropped possessive).",
]},

{
"template_hash": "ba143439c76c2175", "letter_type": "", "specialty": "",
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
Opération oculaire
Extraction des dents de sagesse
Maladie de Von Willebrand !
Problématique psychiatrique
{DATE_HISTORY} : {DX_ABBREV}
Épilepsie de la naissance à la puberté
{DATE_HISTORY} : ulcère anastomotique
Allergies :
---------
Pas d'allergie connue
Traitement à l'admission :
--------------------
- Depakine (comp. chrono 500 mg), 500 mg, {DX_NUMERIC}, {DX_NUMERIC}
- Pantomed (comp. 40 mg), 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
Anamnèse :
---------
Orientation depuis le service de kinésithérapie pour {DIAGNOSIS}.
ATCD GABY. Pas de douleur épigastrique.
En 2012, {DIAGNOSIS} après prise d'Ibuprofène - ne prend désormais que du
Paracétamol.
Encore un ulcère constaté en gastro-entérologie en 2015. Prend chroniquement du Pantomed 40 mg 1 à 2 /j.
CONCLUSION :
--------
Planification d'une hospitalisation de jour pour fer iv, à savoir 1000 mg Injectafer, et
gastroscopie sous sédation.
Problème de {DIAGNOSIS} probablement lié à une malabsorption après
bypass gastrique. Pour cette raison, merci de votre suivi biologique et, si besoin,
de nous réorienter le patient pour fer iv. Également substitution orale en multivitamines
pour éviter d'autres carences.
Gastroscopie en raison d'un {DIAGNOSIS} récidivant antérieurement. Le {PATIENT_NOUN_GENERIC} prend
chroniquement {DX_ABBREV} et évite désormais absolument l'usage de {DX_ABBREV}.
Une ligne prioritaire est disponible en semaine de 8h30 à 17h00, RÉSERVÉE AUX
MÉDECINS, via le numéro de téléphone direct {TELEFOON}.
Bien confraternellement
Cordialement,
{NAME_DOCTOR}
Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
{DATE_VALIDATION}
Validation : {DATE_VALIDATION} 10:37
---------------------------------------------------------------------------
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON}
{STREET} T {TELEFOON} {STREET} T {TELEFOON}
{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "Blank meta.letter_type/specialty, very low extra=12 -- another likely real-seed-derived template (bullet-list surgical history, hardcoded 'gastro-enterologie').",
]},

{
"template_hash": "baee91e407ee68d9", "letter_type": "consultatiebrief", "specialty": "Nefrologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Anamnèse : --------- 03-15-{DX_NUMERIC} : début des symptômes œdème des jambes 07/20{DX_NUMERIC} : diagnostic de {DIAGNOSIS} posé sur base de {DX_TEST} 10/20{DX_NUMERIC} : traitement initial par {DX_DRUG} débuté, réponse sous-optimale {DATE_HISTORY} : aggravation de l'œdème suite à une infection intercurrente ATCD hypertension depuis 20{DX_NUMERIC}, {DX_ABBREV} diabète de type 2 ! Pic de créatinine jusqu'à 187 µmol/L en contexte aigu Pas d'anurie ni d'oligurie rapportée. Pas de dysurie ni de pollakiurie. {PRONOUN_SUBJ} rapporte une diminution du débit urinaire ces 4 derniers jours, pas d'hématurie. Prise alimentaire correcte, restriction hydrique {DX_ABBREV} rétention d'eau. Médication actuelle : ------------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h - Furosémide 40 mg, {DX_NUMERIC}, 9h - Ramipril 5 mg, {DX_NUMERIC}, 9h - Atorvastatine 20 mg, {DX_NUMERIC}, soir Aucun traitement à domicile enregistré : antiacides, AINS, suppléments Examens techniques : ------------------------- À l'arrivée : ----------- - TA : 158/94 mmHg ({DX_ABBREV}) - Température : 36,8°C - IMC : 29,4 - Œdème : ++ aux deux jambes jusqu'au genou ! - Turgescence jugulaire : absente - Pulmonaire : {DX_ABBREV}, sans sibilants ni crépitants - Abdomen : non douloureux, pas d'hépatosplénomégalie - Neurologique : pas de déficit focal Laboratoire ({DATE_ENCOUNTER}) : - DFGe : 48 mL/min/1,73m² (diminution par rapport à 54) - Créatinine : 139 µmol/L ! - Albumine : 36 g/L - HbA1c : 7,1% - K+ : 4,7 mmol/L - Rapport albumine/créatinine urinaire : 42 mg/mmol (microalbuminurie) Conclusion : -------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} atteinte rénale chronique progressive secondaire à {DIAGNOSIS}. Hypertension stable mais protéinurie persistante et DFGe en baisse. Co-existant {DX_ABBREV} nécessite une surveillance attentive. La créatinine reste fluctuante entre 135 et 145 µmol/L ; l'augmentation récente est possiblement associée au statut volémique. --> Suivi de la fonction rénale via bilan trimestriel {DX_ABBREV} {DX_HOMOGRAPH} Conseils : ------- --> Restriction continue de l'apport en sel (<6g/jour) --> Surveiller le statut hydrique, peser quotidiennement à domicile --> Éviter les substances néphrotoxiques (dont les AINS) --> Contrôle en {SPECIALTY} dans trois mois ou plus tôt en cas de progression de l'œdème Nous contacter au {TELEFOON} en cas d'anurie >{DX_NUMERIC} ou de dyspnée Examens techniques : ----------------------- Écho abdomen : {DX_ABBREV}, reins symétriques, pas d'obstruction ECG : rythme sinusal, PQ raccourci, pas de modification ST Échographie rénale : parenchyme épaissi, volume modérément réduit à gauche {DX_ANATOMY} : duplex des artères sans sténose significative {DX_EPONYM} exclu sur base de la clinique et {DX_TEST}

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

    Validation : {DATE_VALIDATION} 08:30
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
    "'haar creatinine blijft fluctueren' (PRONOUN_POSS) -> 'La creatinine reste fluctuante' (dropped possessive).",
]},

{
"template_hash": "bdcd21316f3df9ef", "letter_type": "ontslagbrief", "specialty": "Oncologie",
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

 Cher confrère, Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en consultation en {SPECIALTY}. Motif de consultation -------- {DATE_HISTORY} : {DIAGNOSIS} ! {DX_EPONYM} au contrôle {DX_TEST} {DX_ABBREV} diabète de type 2 Anamnèse psychogériatrique Antécédents familiaux --------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : sensibilité à {DX_DRUG} père : cancer du poumon à 70 ans, décédé en {DX_NUMERIC} Allergies -------- Pas d'allergie connue Traitement à domicile -------------- Aucun traitement à domicile enregistré État ------ {PRONOUN_SUBJ} signale une aggravation de {DX_HOMOGRAPH} depuis {DATE_HISTORY}. ATCD radiothérapie {DX_ABBREV} {DX_ANATOMY} en {DX_NUMERIC}, {DX_ABBREV} {DX_CODESWITCH}. Fatigue, perte d'appétit, perte de poids de 5 kg en 2 mois. Sommeil perturbé {DX_ABBREV} douleur. {PRONOUN_SUBJ} utilise {DX_DRUG_2} de sa propre initiative, {DX_NUMERIC}. Examen clinique ------------------ état général : stable, {AGE_ADJ}, apyrétique HÉMA : {DX_ABBREV} THORAX : normal, pas de ronchi/crépitants ABDOMEN : pas de douleur, pas de tension, pas de {DX_DRUG_2} ! {DX_TEST} : Hb 7,8, CRP 45, {DX_ABBREV} enzymes hépatiques Neurologique : {DX_ABBREV}, coordination {DX_ABBREV} Examen technique ------------------- CT-thorax/abdomen dd {DATE_ENCOUNTER} : progression de {DIAGNOSIS}, métastases hépatiques {DX_ABBREV} PET-scan : activité hypermétabolique au niveau {DX_ANATOMY} et métastases osseuses sacrées Écho cardiologique : FE 55 %, pas d'épanchement péricardique {DX_CODESWITCH} confirme une maladie multifocale Conclusion -------- Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} {DIAGNOSIS} progressive. Il s'agit d'une maladie systémique avec métastases viscérales. {PRONOUN_SUBJ} est ECOG 2. Traitement déjà débuté par {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}. Réponse partielle, mais symptômes persistants. Effets secondaires limités : seulement nausées légères. Pas de complication hématologique à ce jour. --> {SPECIALTY} envisage un passage à {DX_DRUG_2} en association avec {DX_HOMOGRAPH}, après concertation multidisciplinaire. --> consultation psychologie planifiée {DX_ABBREV} adaptation à la maladie chronique. --> suivi toutes les 6 semaines, contrôle {DX_TEST} et statut clinique. --> service social impliqué {DX_ABBREV} soutien à domicile et demande {DX_NUMERIC}.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 11:40
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": []},

{
"template_hash": "bdfad882fd1a51ce", "letter_type": "spoedverslag", "specialty": "Neurologie",
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

    Motif de consultation
    -----------
    {DATE_HISTORY} : {DIAGNOSIS} ! 12/2022 : {DX_EPONYM} {DX_ABBREV}
    {DX_ABBREV}, symptômes prolongés {DX_ABBREV} usage de {DX_DRUG} {PRONOUN_SUBJ} signale une aggravation
    progressive depuis {DX_NUMERIC} semaines

    Antécédents
    ---------------
    {DOB} : jalons de naissance et de croissance normaux 2020 : {DX_TEST}
    réalisé, {DX_CODESWITCH} Problématique psychiatrique :
    {DX_HOMOGRAPH}

    Antécédents familiaux
    -------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_ANATOMY} à 55 ans

    Allergies
    --------
    Pas d'allergie connue

    Traitement à l'admission
    -------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - paracétamol (comp. 1g), 1 comp, 3/j, {DX_NUMERIC} 14h 20h
    Aucun traitement à domicile enregistré

    Anamnèse
    --------
    Orientation depuis la neurologie {DX_ABBREV} ataxie et détérioration mentale. ATCD
    {DX_ABBREV}. {HONORIFIC} signale des difficultés à la marche, une diplopie et de la
    fatigue. Sommeil perturbé {DX_ABBREV} {DX_DRUG_2}. Pas de crise
    épileptique rapportée. {PRONOUN_SUBJ} utilise {TELEFOON} régulièrement pour du soutien.

    État
    ------
    État de conscience normal, bonne coopération, bonne orientation. À
    l'examen : {DX_NUMERIC} mmHg, pouls 78, saturation 97 % air ambiant. Pas d'ictère,
    pas d'adénopathie cervicale {DX_ABBREV}.

    Examen clinique
    ------------------
    Conscience : {DX_HOMOGRAPH}, complète. Motricité : symétrique,
    force musculaire normale proximale/distale, ! hypotonie Coordination : dysmétrie à
    l'épreuve talon-genou, ! également du côté dominant Réflexes : vifs aux membres supérieurs, extension
    plantaire gauche ! Parole : dysarthrie, télégraphique, ! en cas de fatigue
    {DX_ANATOMY} : {DX_ABBREV}, pas de déficit sensitif

    Examen technique
    -------------------
    IRM cérébrale : anomalies progressives de la substance blanche, compatibles avec
    {DIAGNOSIS} EEG : activité pointe-onde interictale
    temporale droite {DX_TEST} : normal, pas d'anomalie
    {DX_CODESWITCH}

    Conclusion
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir :

    Anomalies neurologiques progressives chez le {PATIENT_NOUN_GENERIC}, initialement
    diagnostiquées comme {DX_EPONYM}, avec à présent une évolution nette {DX_ABBREV}
    {DIAGNOSIS}. Réponse insuffisante à {DX_DRUG_2},
    observance vérifiée.

    --> Débuter {DX_DRUG_2} 5mg/jour, titration jusqu'à 20mg/jour sur 4 semaines
    --> Concertation neurologique de contrôle avec {NAME_RELATIVE} planifiée le {DATE_ENCOUNTER}
    --> Orientation vers une consultation de génétique {DX_ABBREV} charge familiale

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 13:31
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
    "'haar mevrouw vermeldt' -- garbled Dutch (stray possessive 'haar' glued onto 'mevrouw'), same class of artifact as the '{HONORIFIC} toestemming gevraagd' pattern found earlier -- read as the patient's own HONORIFIC, stray word dropped.",
    "'is alert, cooperatief' (gendered adjective trap) -> 'Etat de conscience normal, bonne cooperation, bonne orientation' (extends the already-validated 'Conscience normale, orientation normale' fix with an added invariant noun for 'cooperatif/cooperative').",
    "'Progressieve...afwijkingen bij patiente' (Rule 5, bare noun) -> 'chez le {PATIENT_NOUN_GENERIC}' (le always correct since PATIENT_NOUN_GENERIC is invariably 'patient').",
]},

{
"template_hash": "bfa784a23df50b76", "letter_type": "ontslagbrief", "specialty": "Cardiologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                   {NAME_RESPONSIBLE}                    {DATE_ENCOUNTER} 02:00
INSZ{INSZ}          RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère

    Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en
    consultation en {SPECIALTY}.

    Anamnèse :
    ---------
    03/2022 : {DIAGNOSIS} {DX_EPONYM} ! Douleur thoracique
    depuis {DATE_HISTORY}, irradiant vers le bras gauche, {DX_ABBREV} à l'effort. Parfois dyspnée à
    l'effort important, {DX_ABBREV}. Pas de syncope. ATCD {DX_ABBREV}. {RELATIVE_RELATION}
    ({NAME_RELATIVE}) : {DIAGNOSIS} à 58 ans. Pas de
    palpitations ni d'œdème connus. {HONORIFIC} a débuté {DX_DRUG}, {DX_NUMERIC}.

    Médication actuelle :
    ------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - {DX_HOMOGRAPH}, 10 mg, {DX_NUMERIC}, soir
    Aucun traitement à domicile enregistré

    Examens techniques :
    --------------------------
    ECG : rythme sinusal, {DX_NUMERIC} ms QTc. {DX_TEST} {DX_ABBREV}
    Échocardiographie : FEVG 55 %, pas d'anomalie régionale de la cinétique pariétale.
    Holter : pas d'arythmie significative sur 24h.
    {DX_CODESWITCH} Laboratoire : troponine I normale, CRP légèrement
    élevée {DX_NUMERIC} mg/L.

    Conclusion :
    ---------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} douleur thoracique à l'effort. Contrôle le
    {DATE_ENCOUNTER} après diagnostic initial de {DIAGNOSIS}. Cliniquement {DX_ABBREV}
    en dehors de l'effort. ECG et écho stables par rapport aux précédents {DX_ANATOMY}. {PRONOUN_SUBJ}
    rapporte une capacité d'effort limitée, mais pas de symptômes progressifs. Pas
    d'indication de coronarographie invasive pour le moment.
    --> Poursuite du traitement par {DX_DRUG_2} et {DX_DRUG_2}, évaluation
    de l'effet dans 3 mois.
    --> {DX_TEST} en cours via {SPECIALTY}, voir
    {TELEFOON}.

    Conseils :
    ------
    - Pas de tabac, alimentation de type méditerranéen
    - Débuter un parcours actif de revalidation cardiaque, {DX_ABBREV} diabète de type 2
    - Sensibilisation à la nécessité d'un contrôle de la tension et du LDL
    - Nous appeler en cas d'aggravation : douleur >10 min ou dyspnée de repos
    - Ne pas arrêter {DX_DRUG_2} sans concertation
    --> rendez-vous de contrôle le {DATE_ENCOUNTER} en polyclinique {SPECIALTY}

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 13:01
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'zijn {RELATIVE_RELATION}' (PRONOUN_POSS before the relation slot) -> dropped 'zijn', bare '{RELATIVE_RELATION} ({NAME_RELATIVE})'.",
    "'hij gewezen op nood aan controle' (garbled passive) -> 'Sensibilisation a la necessite d'un controle...' (invariant noun-based).",
]},
]

def main():
    out_path = "translated_templates_fr_batch6.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
