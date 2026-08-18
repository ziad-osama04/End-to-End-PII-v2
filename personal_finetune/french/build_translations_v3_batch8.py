# -*- coding: utf-8 -*-
"""Batch 8: 4 more templates."""
import json

TEMPLATES = [
{
"template_hash": "d1551cd6dcdd9efa", "letter_type": "verslag technisch onderzoek", "specialty": "Nefrologie",
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

    Anamnèse
    ------
    Diagnostic de {DIAGNOSIS} posé en 05/2022, traité par
    {DX_DRUG} {DATE_HISTORY} : biopsie rénale réalisée, résultat
    {DX_EPONYM} ! 12/2023 : progression de {DIAGNOSIS},
    début de {DX_DRUG_2} Depuis lors {DX_ABBREV} fatigue et légers
    œdèmes des pieds Plus d'hématurie ni de dysurie depuis {DATE_ENCOUNTER} {PRONOUN_SUBJ} travaille dans
    le secteur du soudage, fume 10/an, pas de consommation d'alcool Co diabète de type 2, bien contrôlé

    Antécédents familiaux
    ---------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : insuffisance rénale à 65 ans Pas de maladie
    héréditaire connue

    Allergies
    --------
    Pas d'allergie connue

    Médication actuelle
    -----------------
    - {DX_DRUG_2}, 10 mg, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 500 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Metformine, 850 mg, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Lisinopril, 10 mg, {DX_NUMERIC}, {DX_NUMERIC}
    - Atorvastatine, 20 mg, {DX_NUMERIC}, 20h
    Aucun traitement à domicile enregistré

    Examen clinique
    ------------------
    T : 36,8°C, TA : 155/92 mmHg, P : 78/min, poids : 82 kg Général : {AGE_ADJ},
    alerte, tenue vestimentaire correcte Peau : pas d'ictère, pas de purpura Thorax : {DX_ABBREV}, pas de
    crépitants Abdomen : souple, dépressible, pas de douleur à la percussion
    {DX_HOMOGRAPH} Membres : léger anasarque jusqu'aux cuisses, pas
    d'ulcération Région rénale : pas de douleur psoas, pas de douleur à la percussion

    Examens techniques
    -------------------------

    Examen : Analyse sérique ({DATE_ENCOUNTER})
    | Paramètre | Résultat | Réf |
    |---------------------|---------------|------------| | Créatinine | 187 µmol/L
    | 60 - 110 | | DFGe | 38 mL/min | > 90 | | Urée | 14,2 mmol/L | 2,5 - 6,5 | |
    Na | 139 mmol/L | 135 - 145 | | K | 4,7 mmol/L | 3,5 - 5,0 | | Albumine | 34
    g/L | 35 - 50 | | HbA1c | 6,4 % | < 6,0 | | Hémoglobine | 10,1 g/dL | 12 - 16
    | | CRP | 5 mg/L | < 5 | | {DX_TEST} | {DX_NUMERIC} | {DX_ABBREV} |

    Rapport albumine/créatinine urinaire ({DATE_ENCOUNTER}) : 86 mg/mmol (réf : <3) !
    Examen microscopique des urines : 15-20 éry, <5 leuc, pas de cylindres Test de la sueur :
    {DX_CODESWITCH}

    Radiologie
    ----------
    Écho abdomen ({DATE_ENCOUNTER}) : rein gauche 8,7 cm, rein droit 9,1 cm,
    échogénicité augmentée, pas d'hydronéphrose. {DX_ANATOMY} intact.

    Conclusion
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} insuffisance rénale progressive dans le cadre de
    {DIAGNOSIS}, diagnostiquée en 2022. {PRONOUN_SUBJ} présente depuis lors
    une fatigue et une tendance œdémateuse croissante. Le laboratoire montre une
    détérioration nette du DFGe jusqu'à 38 mL/min. Protéinurie présente à 86 mg/mmol.
    Le tableau hématologique évoque une anémie de maladie chronique. Bilan
    électrolytique stable. {DX_ABBREV} reste stable.

    --> Coagulation complémentaire en {SPECIALTY} {DX_ABBREV} charge de comorbidités
    --> Maximiser le régime néphroprotecteur : objectif tensionnel <130/80,
    restriction hydrique
    --> Demande de contrôle de suivi de la fonction rénale dans 3 mois
    --> Consultation diététique {DX_ABBREV} régime pauvre en sel et en protéines
    --> Reconsidérer la dose de {DX_DRUG_2} au prochain contrôle

    Conseils
    -----
    - Surveillance tensionnelle à domicile, remplir le protocole et l'apporter
    - Se peser quotidiennement, signaler toute prise >2 kg/3 jours
    - Ne pas prendre d'{DX_ABBREV} ni de substances néphrotoxiques
    - Nous contacter au {TELEFOON} en cas d'oligurie ou d'aggravation sévère de l'œdème
    - Prochain rendez-vous : envoyé automatiquement par le système

    Examens techniques
    --------------------
    - Créatinine sérique et DFGe : voir tableau
    - Rapport albumine/créatinine urinaire : 86 mg/mmol (!)
    - Échographie rénale : taille rénale bilatéralement réduite avec échogénicité augmentée
    - Pas d'anomalie de la paroi vésicale ou {DX_ANATOMY}
    - CT abdomen sans contraste déjà réalisé en 2021 : pas de masse
    - {DX_TEST} récemment réalisé : normal {DX_NUMERIC}
    - {DX_CODESWITCH} interprété comme un tableau stable

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 12:48
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
    "'{DIAGNOSIS} gediagnosticeerd' (gendered-participle trap on DIAGNOSIS) -> 'Diagnostic de {DIAGNOSIS} pose' (agrees with invariant 'diagnostic').",
    "'zij werkt als lasser' -> '{PRONOUN_SUBJ} travaille dans le secteur du soudage' (reuses established fix, avoids gendered profession noun).",
    "'goed in kleermode' (well-dressed, gendered participle trap) -> 'tenue vestimentaire correcte' (invariant noun phrase).",
]},

{
"template_hash": "d2d8524f97dc07a6", "letter_type": "ontslagbrief", "specialty": "Oftalmologie",
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
    ---------
    {DATE_HISTORY} : {DIAGNOSIS} Co {DX_ABBREV} et {DX_EPONYM} !
    Troubles visuels persistants malgré traitement

    Antécédents familiaux :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : rétinite pigmentaire à 50 ans

    Allergies :
    ---------
    Pas d'allergie connue

    Traitement à l'admission :
    --------------------
    - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 goutte, {DX_NUMERIC}, {DX_NUMERIC} 20h

    Anamnèse :
    ---------
    Orientation {DX_ABBREV} perception progressivement altérée {DX_ANATOMY}. ATCD {DX_ABBREV}
    {DX_CODESWITCH}. {PRONOUN_SUBJ} rapporte une vision double depuis {DATE_HISTORY}, avec
    une direction du regard instable. Pas de douleur, mais des phénomènes lumineux au crépuscule.
    Plus de {DX_HOMOGRAPH}. Traitement à domicile enregistré : -
    {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}

    État :
    -------
    La pression oculaire a augmenté, mesurée le {DATE_ENCOUNTER} : {DX_NUMERIC} mmHg à droite,
    {DX_NUMERIC} à gauche. Mauvais suivi médical ces derniers mois. Pas de contrôle
    depuis {DATE_HISTORY}.

    Examen clinique :
    -------------------
    Position oculaire : {DX_ABBREV} Pupilles : isochores, réflexe photomoteur vif Fond d'œil :
    {DX_ANATOMY} ! dégénérescence maculaire liée à l'âge étendue à droite
    Œil myope : {DX_ABBREV}, {DX_TEST} normal Pas de signe de suivi ultérieur

    Examen technique :
    ---------------------
    OCT : {DX_TEST} indiqué, {DX_CODESWITCH} confirme
    Acuité : 0,2 à droite, 0,1 à gauche sans correction Périmétrie : {DX_NUMERIC} %
    de réduction dans le quadrant supérieur droit IOL-master : {DX_NUMERIC} mm

    Conclusion :
    -------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}. À retenir :

    Diagnostic de {DIAGNOSIS} confirmé, avec progression de
    {DX_EPONYM}. Réponse insuffisante à {DX_DRUG_2}, probablement
    {DX_ABBREV} suivi tardif. {PRONOUN_SUBJ} ne rapporte aucun effet secondaire de {DX_DRUG_2}, mais
    indique utiliser rarement les gouttes.

    --> Injection sous-cutanée de {DX_DRUG_2} planifiée le {DATE_ENCOUNTER}, à 10h
    --> Contrôle chez {HONORIFIC} {NAME_PATIENT} le {DATE_ENCOUNTER} {DX_ABBREV} {DIAGNOSIS}
    --> Orientation vers un service de basse vision pour aides visuelles
    --> {TELEFOON} pour toute question

    Aucun traitement à domicile enregistré en dehors des collyres.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 08:27
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'zijn oogdruk is gestegen' (PRONOUN_POSS) -> 'La pression oculaire a augmente' (dropped possessive).",
    "'Controleren bij de heer' (garbled, refers to patient given hij elsewhere) -> 'Controle chez {HONORIFIC} {NAME_PATIENT}' (uses patient's own HONORIFIC slot).",
]},

{
"template_hash": "d63ecf0a45088ed5", "letter_type": "spoedverslag", "specialty": "Reumatologie",
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

    Le {PATIENT_NOUN_GENERIC} susmentionné a été vu au service de {SPECIALTY} le
    {DATE_ENCOUNTER}.

    Antécédents
    -----------------
    {DATE_HISTORY} : {DIAGNOSIS} ! {DX_EPONYM} {DX_ABBREV}
    {DX_ANATOMY} rapporté {DX_ABBREV} Co {DX_HOMOGRAPH} depuis
    {DATE_HISTORY}, traité par {DX_DRUG} Nle cardiovasculaire {DX_ABBREV} {DX_ABBREV}
    {DX_NUMERIC}

    Antécédents familiaux
    --------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_DRUG_2} répondant à
    {DIAGNOSIS} à 70 ans

    Allergies
    ------
    Pas d'allergie connue

    Traitement à l'admission
    -------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    Aucun traitement à domicile enregistré

    Motif de consultation
    ----------
    Admission le {DATE_ENCOUNTER} {DX_ABBREV} gonflement progressif {DX_ANATOMY} et
    douleur dorsale généralisée depuis {DATE_HISTORY}. Aggravation sous {DX_DRUG_2}, selon
    {NAME_RELATIVE}, également plaintes nocturnes, {DX_ABBREV} mauvaise
    qualité de sommeil. {PRONOUN_SUBJ} signale fatigue et amaigrissement {DX_ABBREV}
    {DX_CODESWITCH}.

    État
    ------
    Présentation : {AGE_ADJ}, bon état de conscience, bonne orientation, hémodynamique stable.
    Pas de pic fébrile, temp 37,1°C. {DX_NUMERIC} bas, CRP élevée jusqu'à 48 mg/L.

    Examen clinique
    ------------------
    Général : intègre, pas de cachexie constatée. {DX_ANATOMY} : bilat.
    œdème impressionnant, fluctuation !, douloureux à la palpation, limitation de
    mouvement en degrés. Pas d'érythème, mais sensation de chaleur. {DX_TEST} : positif
    test {DX_HOMOGRAPH} à droite, négatif à gauche. {DX_ABBREV} : neurologique normal.

    Examen technique
    -------------------
    RX {DX_ANATOMY} (réalisé le {DATE_ENCOUNTER}) : modifications arthrosclérotiques,
    pas de fracture ni de luxation. Écho {DX_ANATOMY} : œdème synovial ++, épanchement
    à gauche, modéré à droite. Pas de rupture tendineuse. {DX_CODESWITCH} :
    réactivité {DX_DRUG_2} positive dans le sérum.

    Examens techniques
    ----------------------
    - Écho {DX_ANATOMY} {DATE_ENCOUNTER}
    - CRP / VS {DATE_ENCOUNTER}
    - RX {DX_ANATOMY} {DATE_ENCOUNTER}
    - {DX_TEST} réalisé {DX_ABBREV} suspicion de {DX_EPONYM}

    Conclusion
    --------
    Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} a été orienté depuis {SPECIALTY} {DX_ABBREV} suspicion
    de {DIAGNOSIS}, avec activité persistante malgré
    {DX_DRUG_2}. Antécédent de {DX_HOMOGRAPH} en {DATE_HISTORY},
    symptômes fluctuants depuis lors. Exacerbation actuelle avec augmentation de {DX_NUMERIC} et
    œdème clinique. {PRONOUN_SUBJ} reçoit actuellement {DX_DRUG_2} iv {DX_ABBREV} réponse à
    la dose d'entretien.

    --> Polyclinique gériatrique {SPECIALTY} à envisager, intensification {DX_ABBREV} réponse
    insuffisante.
    --> Attendre les résultats biologiques : anti-{DX_CODESWITCH}, FR.
    --> Consultation hématologie {DX_ABBREV} {DX_NUMERIC} bas et tableau inflammatoire.
    --> Prochain contrôle planifié dans 4 semaines. {TELEFOON} accessible en cas de
    symptômes intercurrents.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 13:07
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
    "Rule 4 applied: dropped 'de heer' before {NAME_RELATIVE}.",
    "'hij toegelaten op X' / 'hij presenteert als X patient, alert, orient' -- two gendered-participle traps -> restructured as invariant-noun-subject sentences ('Admission le...', 'Presentation : X, bon etat de conscience, bonne orientation...').",
]},

{
"template_hash": "d8cba941ea3e1109", "letter_type": "consultatiebrief", "specialty": "Dermatologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                   {NAME_RESPONSIBLE}                  {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}             ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère

    Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_ENCOUNTER} en
    consultation en {SPECIALTY}.

    Motif de consultation :
    -----------
    {DATE_HISTORY} : {DIAGNOSIS} {DX_EPONYM} ! Co
    symptômes dermatologiques depuis plusieurs mois

    Antécédents familiaux :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : sensibilité à {DX_DRUG}

    Allergies :
    ---------
    Pas d'allergie connue

    Traitement à domicile :
    ----------------
    Aucun traitement à domicile enregistré

    Antécédents :
    ----------------
    05/2023 : suspicion initiale {DX_ABBREV} {DATE_HISTORY} : biopsie {DX_ANATOMY} →
    {DX_CODESWITCH} ATCD eczéma, {DX_ABBREV} {DX_HOMOGRAPH}

    Anamnèse :
    -------
    {PRONOUN_SUBJ} signale des démangeaisons et une desquamation persistantes au niveau {DX_ANATOMY}, progressives.
    Pas de fièvre, pas de sueurs nocturnes. Pas de voyage récent ({DX_NUMERIC}). Mauvaise
    réaction aux crèmes en vente libre. Utilisation de {DX_DRUG_2} sans
    effet.

    Examen clinique :
    -------------------
    {DX_ANATOMY} : érythème, infiltration, {DX_ABBREV}. ! {DX_TEST} Pas
    d'adénopathie régionale. Pas d'éruption induite par {DX_DRUG_2}. Peau : sèche,
    avec plaques et squames argentées.

    Examen technique :
    --------------------
    Biopsie {DX_ANATOMY} réalisée le {DATE_ENCOUNTER}. Histopathologie en
    cours. Demande {DX_CODESWITCH}.

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, {DX_ABBREV} {DIAGNOSIS}, statut post
    biopsie. {DX_EPONYM} suspecté, diagnostic définitif en attente de
    l'histologie.

    --> Débuter {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    --> Suivi dans {DX_NUMERIC} semaines pour discuter du résultat
    --> Nous contacter en cas d'aggravation : {TELEFOON}

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 09:34
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": []},
]

def main():
    out_path = "translated_templates_fr_batch8.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
