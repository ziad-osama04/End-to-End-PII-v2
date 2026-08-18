# -*- coding: utf-8 -*-
"""Batch 2 of the v3-based French template translation: 5 more templates."""
import json

TEMPLATES = [
{
"template_hash": "4f8a641c39215d45", "letter_type": "ontslagbrief", "specialty": "Dermatologie",
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

 Le {PATIENT_NOUN_GENERIC} susmentionné a été vu au service de {SPECIALTY} le {DATE_ENCOUNTER}. Antécédents : ----------------- 15-03-{DX_NUMERIC} : {DIAGNOSIS} 04/2020 : {DX_EPONYM} ! Dermatite atopique depuis l'enfance ATCD {DX_ABBREV}, {DX_ABBREV} diabète de type 2 Antécédents familiaux : ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}) : psoriasis à 50 ans Allergies : --------- Pas d'allergie connue Anamnèse : --------- Orientation par le médecin traitant {DX_ABBREV} {DIAGNOSIS}. {PRONOUN_SUBJ} se plaint de plaques érythémateuses prurigineuses au niveau {DX_ANATOMY} depuis {DX_NUMERIC} semaines. Pas de fièvre. Pas de voyage récent ({DX_ABBREV}). Pas d'amélioration sous {DX_DRUG} prescrit par le médecin traitant. {PRONOUN_SUBJ} utilise parfois {DX_HOMOGRAPH} acheté en pharmacie, sans ordonnance. Examen clinique : -------------------- {DX_ANATOMY} : érythème, desquamation, légère exsudation ! Pas de {DX_ABBREV}. Pas de {DX_TEST} indiqué. Peau : {DX_ABBREV}. {DX_CODESWITCH} Conclusion : ------- Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} a été évalué le {DATE_ENCOUNTER}. À retenir : --> Débuter un traitement topique : - {DX_DRUG_2} pommade, {DX_NUMERIC}, {DX_NUMERIC} 20h - Bepanthen crème, {DX_NUMERIC}, le soir --> Éviter les produits irritants. Plus de {DX_DRUG_2}. --> Suivi en consultation {SPECIALTY} dans 6 semaines. --> Biopsie {DX_ANATOMY} planifiée {DX_ABBREV} {DX_EPONYM} ! Aucun traitement à domicile enregistré en dehors de {DX_HOMOGRAPH}. Conseil donné à {HONORIFIC} {NAME_PATIENT} de nous contacter au {TELEFOON} en cas d'aggravation.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:49
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
    "'Bovengenoemde patient werd gezien' / 'De X patient werd beoordeeld' (passive) -> 'Le {PATIENT_NOUN_GENERIC} susmentionne a ete vu' / 'Le {PATIENT_NOUN_GENERIC} X a ete evalue' -- PATIENT_NOUN_GENERIC is always literal 'patient' (masculine invariant), so the participle safely agrees with it regardless of the sampled patient's actual sex.",
    "'de heer geadviseerd contact op te nemen' (garbled, patient's own honorific given PRONOUN_SUBJ=hij used earlier) -> 'Conseil donne a {HONORIFIC} {NAME_PATIENT} de nous contacter' (invariant-noun-as-subject fix).",
]},

{
"template_hash": "54a3df68e967b757", "letter_type": "spoedverslag", "specialty": "Dermatologie",
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

    Motif de consultation :
    -----------
    {DATE_HISTORY} : {DIAGNOSIS} ! Co {DX_ABBREV}, {DX_ABBREV} réaction cutanée
    notable après usage de {DX_DRUG} ATCD {DX_EPONYM}, par ailleurs
    sans particularité

    Antécédents familiaux :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DIAGNOSIS} à {DX_NUMERIC}
    ans

    Allergies :
    ---------
    Pas d'allergie connue

    Traitement à l'admission :
    --------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Si besoin en cas de réaction allergique

    Anamnèse :
    ---------
    {PRONOUN_SUBJ} signale un début aigu de prurit et d'éruption au niveau {DX_ANATOMY}
    Aggravation à l'exposition au soleil et à la chaleur Aucun traitement à domicile
    enregistré en dehors de {DX_DRUG_2} {DX_ABBREV} symptômes

    Examen clinique :
    --------------------
    {DX_ANATOMY} : érythème avec composante papulo-pustuleuse, ! pas d'aspect
    infectieux. {DX_HOMOGRAPH}. {DX_TEST} : négatif le
    {DATE_HISTORY}

    Examen technique :
    -------------------
    Biopsie {DX_ANATOMY} réalisée le {DATE_HISTORY} Résultat en attente

    Conclusion :
    ------
    Le {PATIENT_NOUN_GENERIC} {AGE_ADJ} a été orienté depuis {SPECIALTY} {DX_ABBREV}
    symptômes cutanés récidivants. Co dermatite, possiblement liée au médicament
    {DX_ABBREV} {DX_DRUG_2}. Pas d'infection évidente, mais {DX_CODESWITCH}
    non exclu.

    --> Attendre les résultats de l'examen technique
    --> Pas de changement de traitement en attendant le résultat {DX_TEST}
    --> Consultation {SPECIALTY} en cas d'aggravation ou de nouvelles éruptions

    Examens techniques :
    -----------------------
    Examen histologique biopsie cutanée {DX_ANATOMY} – {DX_NUMERIC}

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 12:16
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
    "v3 rework: DIAGNOSIS/RELATIVE_RELATION now properly slotted.",
    "'De X patient werd doorverwezen' -> 'Le {PATIENT_NOUN_GENERIC} X a ete oriente' (invariant subject).",
]},

{
"template_hash": "6b62dd0ae9cfa4ed", "letter_type": "ontslagbrief", "specialty": "NKO",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                     {NAME_RESPONSIBLE}                {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère,

    Nous avons vu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} en consultation en {SPECIALTY} le
    {DATE_ENCOUNTER}.

    Anamnèse :
    --------
    12-03-{DX_NUMERIC} : début des symptômes, œdème du genou droit sans traumatisme 05/2024 :
    ménorragie ; suspicion : {DIAGNOSIS} {DATE_HISTORY} : {DX_ABBREV}
    {DX_ABBREV}, {DX_DRUG} instauré {DX_ABBREV} hypertension. {HONORIFIC} signale une douleur au niveau
    {DX_ANATOMY}, s'aggravant depuis 2 semaines à l'effort ! Orientation depuis le
    médecin traitant {DX_ABBREV} {DX_TEST} et tableau arthritique peu clair.
    {PATIENT_NOUN_MARKED} {AGE_ADJ}, présente {DX_ABBREV} {DX_EPONYM}. {PRONOUN_SUBJ} travaille
    dans le secteur du soudage et rapporte des difficultés à se pencher et à porter des charges. Pas de fièvre,
    pas de perte de poids. Pas d'uvéite ni d'atteinte cutanée rapportée. {RELATIVE_RELATION} ({NAME_RELATIVE})
    présente {DX_HOMOGRAPH}, diagnostic posé à 38 ans.

    Antécédents familiaux :
    --------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : {DX_CODESWITCH} à l'âge {DX_NUMERIC}
    {RELATIVE_RELATION} : {DX_ABBREV} diabète de type 2

    Allergies :
    ---------
    Pas d'allergie connue

    Médication actuelle :
    ------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - Paracétamol 1g, 1 comp, 3/j, prn
    - {DX_DRUG_2}, 2,5 mg, {DX_NUMERIC}, matin
    - Voltaren suppo, 75 mg, {DX_NUMERIC}, soir
    - Simvastatine, 20 mg, {DX_NUMERIC}, soir
    Aucun traitement à domicile enregistré

    Examens techniques :
    --------------------------
    Radiographie genou droit (14-03-{DX_NUMERIC}) : modifications arthrosclérotiques, {DX_ABBREV}
    fracture ou luxation IRM genou droit (20-03-{DX_NUMERIC}) : déchirure méniscale médiale
    grade II, petit épanchement ! Échographie poignet : pas de synovite ni de ténosynovite
    Laboratoire (21-03-{DX_NUMERIC}) : CRP 8 (<5), VS 12, Hb 13,8,
    plaquettes normales ASLO : {DX_ABBREV}, FR : nég, anti-CCP : nég Test DX
    réalisé : {DX_TEST}

    Examen clinique :
    -------------------
    Genou : flexion diminuée jusqu'à 110°, douloureux à la mobilisation passive en extension !
    {DX_ANATOMY} : gonflé, sensation de chaleur, crépitations à la mobilisation
    Température corporelle : 36,8°C Neurovasculaire : pulsations intactes, sensibilité
    et motricité distales Palpation musculaire : {DX_ABBREV} {DX_HOMOGRAPH}

    Conclusion :
    --------
    --> {PATIENT_NOUN_MARKED} {AGE_ADJ} avec gonalgie subaiguë droite, associée à une
    limitation fonctionnelle.
    --> Aspect arthrosclérotique à la radiographie, l'IRM montre une déchirure méniscale sans tableau
    opérable en urgence.
    --> Gonarthrose {DX_ANATOMY} avec synovite secondaire, voir
    {DX_TEST}.
    --> Diagnostic différentiel : {DX_EPONYM} actuellement moins
    probable {DX_ABBREV} résultats de laboratoire et évolution.
    Pas d'indication chirurgicale orthopédique pour le moment. Kinésithérapie déjà
    débutée, {DX_ABBREV} effet positif.

    Conseils :
    -------
    - Poursuite de la kinésithérapie, axée sur le renforcement du quadriceps et la proprioception
    - Diminution progressive des suppositoires ; éventuel passage à voie orale {DX_ABBREV} si nécessaire (surveiller le risque de gastrite)
    - Poursuivre {DX_DRUG_2}, contrôle tensionnel dans 1 mois via {TELEFOON}
    - Nouveau contrôle {SPECIALTY} dans 8 semaines pour évaluer la réponse
    - En cas de symptômes progressifs ou d'instabilité : consultation en urgence
    - Avis pour l'employeur : aménagement temporaire du port de charges (max 10 kg) {DX_ABBREV} médecine du travail
    - Bilan demandé vu {DIAGNOSIS} et {DX_ABBREV}, résultat à venir
    - {PATIENT_NOUN_GENERIC} informé du pronostic et du rôle de la modification du mode de vie

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:17
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "'verwacht {DIAGNOSIS}' (suspected X, gendered participle trap) -> ' ; suspicion : {DIAGNOSIS}' colon-label style.",
    "'haar zus ({RELATIVE_RELATION}) heeft X, gediagnosticeerd' -- redundant Dutch phrasing (zus + RELATIVE_RELATION both mean the same sampled relation) AND a possessive+gendered-participle trap -> dropped 'haar zus', kept only '{RELATIVE_RELATION} ({NAME_RELATIVE}) presente X, diagnostic pose a 38 ans' (diagnostic/pose invariant masculine).",
    "'zij werkt als lassers' (gendered profession noun tied to patient) -> '{PRONOUN_SUBJ} travaille dans le secteur du soudage' (invariant, sector-based phrasing instead of a gendered job-title noun).",
]},

{
"template_hash": "6da62e5b62204503", "letter_type": "verslag technisch onderzoek", "specialty": "Nefrologie",
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
    --------
    03/2018 : {DIAGNOSIS} diagnostiqué {DATE_HISTORY} : instauration
    initiale de {DX_DRUG}, réponse sous-optimale Ces 2 derniers mois : augmentation
    de la fatigue, œdème des chevilles ! Polyurie nocturne, {DX_ABBREV} soif. Pas de dysurie.
    Nie toute douleur rénale. ATCD {DX_ABBREV}. Co diabète de type 2. En outre
    {DX_EPONYM} ! Antécédents familiaux : père ({NAME_RELATIVE}) décédé d'un AVC à
    72 ans

    Allergies
    ---------
    Pas d'allergie connue

    Traitement à domicile
    -------------
    - {DX_DRUG_2}, 5 mg, {DX_NUMERIC}, {DX_NUMERIC}
    - Metformine 850 mg, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - Atorvastatine 20 mg, 1 comp, le soir
    - {DX_DRUG_2}, {DX_NUMERIC}

    Médication actuelle
    ---------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - Metformine, {DX_NUMERIC}, {DX_NUMERIC} 20h
    - {DX_HOMOGRAPH}, {DX_NUMERIC}
    Aucun traitement à domicile enregistré

    Examen clinique
    ------------------
    Général : {AGE_ADJ}, alerte, normocéphale. Œdème remontant au-dessus des genoux ++ ! TA :
    168/94 mmHg. FC : 82 bpm. IMC : 31,4 Thorax : murmure {DX_ABBREV}. Pas de galop.
    Abdomen : sensible en paravertébral gauche en zone lombaire. Pas de défense.
    {DX_ANATOMY} : {DX_ABBREV} Membres : œdème godet ++ aux membres inférieurs, douleur à
    la flexion dorsale

    Laboratoire (dans les 2 semaines)
    -----------------------------
    Créatinine : 186 µmol/L ↑ DFGe : 38 mL/min/1,73m² ↓ Potassium : 5,4 mmol/L ↑
    Albumine : 32 g/L ↓ HbA1c : 7,6 % Bandelette urinaire : protéinurie 3+, hématurie +
    {DX_TEST} : positif pour microalbuminurie, ratio 45 mg/mmol

    Examens techniques
    -------------------------

    Examen Résultat Référence
    ----------------------------  --------------------    --------------
    Créatinine (sérum) {DX_NUMERIC} µmol/L 60 – 110 DFGe 38 mL/min >90
    Potassium                      5,4 mmol/L              3,5 – 5,0
    Sodium                         139 mmol/L              135 – 145
    Hémoglobine                    10,8 g/dL               13,0 – 17,0
    VGM                            91 fL                   80 – 100
    Albumine                       32 g/L                  35 – 50
    CRP 5 mg/L <5 Rapport albumine/créatinine urinaire 45 mg/mmol <3,5

    Conclusion
    -------
    {PATIENT_NOUN_MARKED} {AGE_ADJ}. Antécédent : {DIAGNOSIS}, depuis {DATE_HISTORY}.
    Détérioration récente de la fonction rénale {DX_ABBREV} possible atteinte glomérulaire
    progressive. Protéinurie 3+ et DFGe abaissé sont ! en faveur d'une insuffisance rénale
    chronique. {PRONOUN_SUBJ} présente une hypertension et un diabète {DX_ABBREV}, tous deux
    impliqués dans la pathogenèse {DX_CODESWITCH}. HbA1c stable mais contrôle tensionnel
    sous-optimal.

    Conseils
    ------
    --> Optimisation des antihypertenseurs : passage de {DX_DRUG_2} à un
    inhibiteur de l'ECA sous surveillance créatinine/potassium
    --> Répéter la bandelette urinaire et la créatinine dans 14 jours
    --> Orientation {DX_ABBREV} conseil diététique {DX_ABBREV} interaction avec {DX_DRUG_2} et obésité
    --> Consultation équipe {DX_EPONYM} {DX_ABBREV} biopsie éventuelle si
    protéinurie progressive
    --> Échographie {DX_ANATOMY} planifiée le {DATE_ENCOUNTER}

    Examens techniques
    ----------------------
    Échographie abdomen : reins légèrement diminués de taille, asymétriques, rein gauche 9,1 cm,
    droit 10,4 cm. Structure perturbée, surtout à gauche. Pas de dilatation des voies urinaires.
    Doppler : bonne perfusion intrarénale, RI 0,72 bilatéral. Pas de thrombose.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 10:05
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}  T {TELEFOON}
    {STREET}  T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 2 applied: 'X patient met anamnestisch {DIAGNOSIS} connu(e)' -> '{PATIENT_NOUN_MARKED} {AGE_ADJ}. Antecedent : {DIAGNOSIS}, depuis {DATE_HISTORY}.' (colon-label, no agreement/elision risk).",
]},

{
"template_hash": "70ecb4b6ba667b75", "letter_type": "opvolgbrief", "specialty": "Pneumologie",
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

    UNITÉ : 32596 DATE : {DATE_ENCOUNTER} ORIGINE : asiatique ÂGE :
    {AGE} TAILLE 165,5 cm POIDS : 109,9 kg IMC :
    40,142 TABAGISME : non connu

    Antécédents :
    -----------------
    04/2018 : {DIAGNOSIS} {DX_EPONYM} ! Toux chronique
    depuis 5 ans, progressive

    Antécédents familiaux :
    ----------
    mère ({NAME_RELATIVE}) : asthme à {AGE_ADJ} père : décédé à
    72 ans {DX_ABBREV} de complications liées à {DX_DRUG}

    Allergies :
    ---------
    Pas d'allergie connue

    Traitement à l'admission :
    ---------------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - {DX_HOMOGRAPH}, 2 bouffées, prn
    - salbutamol (inhalation 100 mcg), 1-2 bouffées, prn

    Anamnèse :
    --------
    {PRONOUN_SUBJ} revient après une première consultation le {DATE_HISTORY}. Plaintes d'essoufflement
    à l'effort minime, surtout en montant les escaliers et en marchant contre le vent. Signale aussi
    une toux productive matinale avec expectorations blanches, pas d'hémoptysie. Plus de plaintes
    nocturnes depuis le début {DX_NUMERIC}. Sommeil non perturbé. Pas de fièvre. Pas
    d'infection récente.

    ATCD {DX_ABBREV} {DX_ABBREV} {DX_ABBREV}. Pas de composante allergique prouvée. Travaille en
    jardinerie : exposition aux moisissures et à la poussière de bois reste envisageable comme
    facteur déclenchant. Pas d'animaux au domicile. Un masque anti-poussière au travail a déjà été
    conseillé à {HONORIFIC} {NAME_PATIENT}, mais l'application reste irrégulière {DX_ABBREV}
    {DX_CODESWITCH}.

    Par ailleurs {DX_ABBREV} médical : HTA, bien contrôlée sous {DX_DRUG_2}. Pas de
    diabète. Co dysfonction hépatique d'étiologie {DX_ABBREV}.

    {PATIENT_NOUN_MARKED} rapporte une tolérance à l'effort réduite par rapport à l'an dernier.
    Se dit « à bout de forces » après les courses quotidiennes. Pas de cyanose ni d'œdème
    signalé à domicile. Utilisation limitée de l'inhalateur prn, mais signale que l'effet diminue.

    Médication actuelle :
    ----------------
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}
    - amlodipine, 5 mg, {DX_NUMERIC}
    - salbutamol, 2 bouffées, prn – dernière utilisation : il y a 3 jours
    - {DX_HOMOGRAPH}, 1 comp, {DX_NUMERIC}
    - paracétamol, 1 g, 3/j, prn

    Examens techniques :
    --------------------------
    SANG : {DATE_ENCOUNTER}
    - Hb : 13,8 g/dL
    - CRP : 6 mg/L
    - BNP : 98 ng/L
    - {DX_TEST} : normal
    SPIROMÉTRIE : {DATE_ENCOUNTER}
    - VEMS : 68 % préd
    - CVF : 82 % préd
    - VEMS/CVF : 0,61 !
    - DLCOSB : 64 % préd !
    → confirme un trouble ventilatoire obstructif de sévérité modérée, réversibilité partielle
    (VEMS +12 %, +210 mL après bronchodilatateur) RX THORAX : {DATE_ENCOUNTER}
    - hypertransparence des champs pulmonaires basaux
    - cœur en position verticale
    - coupoles diaphragmatiques abaissées
    - pas d'infiltrats, pas d'épanchement pleural
    - {DX_ANATOMY} : {DX_ABBREV}
    CT-THORAX HR : {DATE_ENCOUNTER}
    - modifications emphysémateuses surtout basales
    - wall thickening bronchique
    - pas de malignité
    - pas de signe d'hypertension pulmonaire
    GAZOMÉTRIE : {DATE_ENCOUNTER}
    - pH : 7,40
    - pCO2 : 5,1 kPa
    - pO2 : 9,8 kPa
    - saturation : 96 % air ambiant

    Conclusion :
    --------
    Nous avons revu {NAME_PATIENT}, {PATIENT_NOUN_MARKED} {AGE_ADJ}, en contrôle en {SPECIALTY} {DX_ABBREV}
    symptômes obstructifs chroniques. Confirmé : {DIAGNOSIS} sur base de
    la spirométrie et de l'imagerie.

    Cliniquement stable, mais symptômes persistants malgré le traitement de base.
    Limitation fonctionnelle présente, corrigée pour l'âge et le sexe. Pas
    d'aggravation aiguë. Réactivité au bronchodilatateur présente mais limitée.

    --> Optimisation du traitement : début {DX_DRUG_2} via DPI, {DX_NUMERIC} +
    spirométrie de contrôle dans 3 mois.
    --> Conseil de sevrage tabagique si disponible via {DX_CODESWITCH},
    malgré une anamnèse tabagique négative.
    --> Statut vaccinal vérifié : complet (grippe, pneumocoque).

    Conseils :
    -------
    - Orientation vers la revalidation pulmonaire en concertation avec le médecin traitant.
    - Contrôle en polyclinique {SPECIALTY} dans 12 semaines.
    - {TELEFOON} disponible en cas d'urgence.
    - Informer sur la reconnaissance des exacerbations : changement des expectorations, fièvre, aggravation respiratoire.
    - Recommander un aménagement du poste {DX_ABBREV} exposition, envisager une candidature dans un autre secteur.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 12:06
    ------------------------------------------------------------------
    {STREET}              T {TELEFOON}
    {STREET}              T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 5 applied: bare 'patiente rapporteert' (not caught by the automated risky-word scan, only HONORIFIC/PRONOUN_SUBJ are scanned) -> '{PATIENT_NOUN_MARKED} rapporte' -- manually caught during translation.",
    "'mevrouw werd reeds geadviseerd inzake stofmasker' -> 'Un masque anti-poussiere ... a deja ete conseille a {HONORIFIC} {NAME_PATIENT}' (invariant-noun-as-subject fix, masque=masculine).",
    "Quoted self-description '\"uitgeput\"' (exhausted, gendered adjective in Dutch quote) -> quoted idiom '« a bout de forces »' -- gender-invariant fixed expression, preserves the quoted-speech register without a bracket stopgap.",
]},
]

def main():
    out_path = "translated_templates_fr_batch2.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
