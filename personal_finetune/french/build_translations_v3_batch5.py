# -*- coding: utf-8 -*-
"""Batch 5: 4 more templates."""
import json

TEMPLATES = [
{
"template_hash": "a4801db8d8f91d5f", "letter_type": "spoedverslag", "specialty": "NKO",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}             {NAME_RESPONSIBLE}                   {DATE_ENCOUNTER} 02:00
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
    {DATE_HISTORY} : {DIAGNOSIS} 03/2024 : {DX_EPONYM}, ! {DX_ABBREV}
    fièvre, symptômes persistants {DX_ABBREV} Problématique psychiatrique, {DX_ABBREV} dépression et
    {DX_HOMOGRAPH}
    Antécédents familiaux :
    ----------
    {RELATIVE_RELATION} ({NAME_RELATIVE}) : sensibilité à {DX_DRUG} à 50 ans

    Allergies :
    ----------
    Pas d'allergie connue

    Traitement à l'admission :
    -------------------
    - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, 9h
    - Paracétamol (comp. 1g), {DX_NUMERIC}, {DX_NUMERIC} 20h
    - {DX_DRUG_2}, 1 suppo, 1/n, au coucher
    Aucun traitement à domicile enregistré

    Médication actuelle :
    ----------------
    - {DX_DRUG_2}, 50mg, {DX_NUMERIC}, le matin
    - {DX_ABBREV}, {DX_NUMERIC}, {DX_NUMERIC}, {DX_NUMERIC}

    Examens techniques :
    --------------------------
    ECG : {DX_CODESWITCH}, {DX_ABBREV} rythme sinusal, {DX_ABBREV} Écho abdominale : pas de
    lignes au niveau {DX_ANATOMY}, {DX_ABBREV} Laboratoire : Hb {DX_NUMERIC}, CRP élevée
    jusqu'à 120, ! PCR pour {DX_TEST} négative

    Anamnèse :
    ---------
    {PATIENT_NOUN_MARKED} {AGE_ADJ} signale une douleur aiguë au flanc gauche depuis {DATE_ENCOUNTER}. Apparition
    aiguë, ATCD calculs rénaux en 2019. Douleur irradiant vers l'aine, associée
    à une hématurie intermittente. Pas de dysurie. Pas de fièvre. Transit correct. Co
    {DIAGNOSIS} !

    Examen clinique :
    -------------------
    Abdomen : sensible à gauche, {DX_ANATOMY} positif signe de Gerota ! FR : {DX_ABBREV},
    pas d'anomalie Neurologique : {DX_TEST} dans les limites de la normale

    Conclusion :
    --------
    --> {SPECIALTY} : exclure des complications de
    {DIAGNOSIS}. Douleur de flanc aiguë avec hématurie, !
    suspicion d'étiologie infectieuse ou vasculaire ({DX_DRUG_2} ?).

    Conseils :
    -------
    - CT-scan abdomen avec contraste : indiqué {DX_ABBREV} {DX_CODESWITCH}
    - Répéter hémogramme, culture d'urine
    - Hydratation iv en cas de symptômes persistants
    - Nous contacter au {TELEFOON} en cas d'augmentation de la douleur ou de fièvre

    Examens techniques :
    -----------------------
    - Écho {DX_ANATOMY} : normale
    - Bandelette urinaire : sang ++, leucocytes +
    - Échographie : pas d'hydronéphrose, ! mais zone hypo-échogène au niveau du rein gauche

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 16:53
    ------------------------------------------------------------------
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}
    {STREET}          T {TELEFOON}

    {STREET}        T {TELEFOON}
    {STREET}        T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "Rule 5 applied: 'De X patient meldt' -> '{PATIENT_NOUN_MARKED} X signale'.",
]},

{
"template_hash": "a733c617b8ae2b93", "letter_type": "", "specialty": "",
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
Nous avons reçu votre {PATIENT_NOUN_GENERIC} {NAME_PATIENT} ({DOB}) le {DATE_HISTORY}
en consultation en {SPECIALTY}.
Anamnèse
--------
{DX_ABBREV} diabète
Médication actuelle
-----------------
- Asaflow (comp. 80 mg), 80 mg, {DX_NUMERIC}, {DX_NUMERIC}
- Atorstatine (comp. 20 mg), 20 mg, {DX_NUMERIC}, {DX_NUMERIC}
- D-cure (caps {DX_NUMERIC}), 25000 UI, 1 fois toutes les 4 semaines
- {DX_DRUG} (fl inj 1 mg), 1 mg, SC, {DX_NUMERIC}
- Insuline lyumjev (stylo {DX_NUMERIC}), 0 UI, SC, {DX_NUMERIC}, {DX_NUMERIC}
- Insuline lyumjev (stylo 200 e/ml 3 ml), 16 UI, SC, {DX_NUMERIC}, {DX_NUMERIC}
- Insuline lyumjev (stylo 200 e/ml 3 ml), 10 UI, SC, {DX_NUMERIC}, {DX_NUMERIC}
- Insuline lyumjev (stylo 200 e/ml 3 ml), 16 UI, SC, {DX_NUMERIC}, 17h
- Insuline toujeo (solostar stylo {DX_NUMERIC}), 12 UI, SC, {DX_NUMERIC}
- Lambipol (comp disp 100 mg), 100 mg, {DX_NUMERIC}, {DX_NUMERIC} {DX_NUMERIC}
- L-thyroxine (comp. 50 mcg), 50 mcg, {DX_NUMERIC}
- Metformine viatris (comp. 500mg), 500 mg, {DX_NUMERIC} {DX_NUMERIC} {DX_NUMERIC}
- Nexiam (comp. 20 mg), 20 mg, {DX_NUMERIC}, 7h
- Ozempic (stylo prérempli 1 mg), {DX_NUMERIC}, SC, {DX_NUMERIC}
- Progor (caps retard 180 mg), 180 mg, {DX_NUMERIC}, {DX_NUMERIC}
- Sipralexa (comp. 20 mg), 20 mg, {DX_NUMERIC} Examen clinique
------------------
Acuité visuelle :
Loin {DX_ABBREV} : 1.0, {DX_CODESWITCH} (-0.25 ^ -0.25 axe 165°)
1.0, {DX_CODESWITCH} (-0.25 ^ -0.25 axe 165°)
Loin {DX_ABBREV} : 1.0, {DX_CODESWITCH} (+0.00 ^ -1.00 axe 2°)
1.0, {DX_CODESWITCH} (+0.00 ^ -1.00 axe 2°)
Lecture {DX_ABBREV} : {DX_TEST} a nl ods ; {DX_TEST} a nl ods.
Lecture {DX_ABBREV} : {DX_TEST} ; {DX_TEST}.
Biomicroscopie :
{DX_ABBREV} : nl
Tension oculaire :
{DX_ABBREV} {DX_ABBREV} : 12.0 mmHg
{DX_ABBREV} {DX_ABBREV} : 14.0 mmHg
Examen du fond d'œil :
{DX_ABBREV} (dilaté) : pas de rétinopathie diabétique
Examens techniques
-------------------------
{DX_TEST} :
{DX_ABBREV} : {DX_ABBREV} sensibilité.
Conclusion
-------
pas de rétinopathie diabétique
{DX_ABBREV} dilatation 1 an.
Bien confraternellement
Cordialement, également au nom de
{NAME_DOCTOR} {NAME_DOCTOR_2}
{NAME_DOCTOR_3}
{NAME_DOCTOR_4}
{NAME_DOCTOR_5}
{NAME_DOCTOR}
{NAME_DOCTOR_5}
{NAME_DOCTOR_5}
{NAME_DOCTOR_5}
{NAME_DOCTOR_5}
{NAME_DOCTOR_5} {NAME_DOCTOR_5}
{NAME_DOCTOR_5}
Ce rapport a été validé électroniquement par {NAME_DOCTOR} le {DATE_VALIDATION}
Validation : {DATE_VALIDATION} 11:11
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
    "Blank meta.letter_type/specialty, ophthalmology-specific content (visual acuity notation, fundus exam), likely another real-seed-derived template like 7fed825dd1a65d86/910ee8bd5e921c1b.",
    "Repeated '{NAME_DOCTOR_5}' many times in the signature block is a literal source artifact (garbled multi-signature-stamp OCR noise) -- preserved as-is rather than 'cleaned', since it matches realistic messy real-letter structure the OOD/augmentation layers are meant to be robust to.",
]},

{
"template_hash": "b16b7f45361c7688", "letter_type": "spoedverslag", "specialty": "Urologie",
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
    --------
    {DATE_HISTORY} : dysurie soudaine avec hématurie ! {PRONOUN_SUBJ} rapporte de la fièvre et
    des ténesmes, depuis hier. ATCD {DX_ABBREV}, {DX_ABBREV} {DX_DRUG}.
    {DX_EPONYM} dans la famille ({RELATIVE_RELATION} : {NAME_RELATIVE}). Pas de douleur de flanc
    ni d'œdème. Pas de {DX_HOMOGRAPH}. Déjà 1x antibiotiques iv
    (ceftriaxone) {DX_ABBREV} suspicion de {DIAGNOSIS}.

    Médication actuelle
    -----------------
    - Aucun traitement à domicile enregistré
    - {DX_DRUG_2}, 500 mg, 3/j, {DX_NUMERIC}
    - {DX_DRUG_2}, 10 mg, {DX_NUMERIC}, 9h
    - Paracétamol (comp. 1 g), 1 g, 4/j, si douleur

    Examen clinique
    ------------------
    Température : 38,2 °C. Tension : 134/82 mmHg. {DX_NUMERIC} mesuré. Abdomen :
    douleur libre à gauche, pas de défense. {DX_TEST} + à gauche. {DX_ANATOMY} :
    douleur à la percussion à gauche ! Sédiment urinaire : urine claire, pas de pus, sang microscopique
    ++.

    Examens techniques
    -------------------------
    Écho abdomen : {DX_CODESWITCH}, suspicion de calcul urinaire à gauche.
    CT-appareil urinaire (sans contraste) : calcul de 6 mm dans l'uretère distal
    gauche, dilatation urétérale proximale. {DX_TEST} : leucocytose 14,5
    x10⁹/L, CRP 48 mg/L.

    Conclusion
    --------
    {PATIENT_NOUN_MARKED} {AGE_ADJ}. Prise en charge aux urgences avec orientation vers {SPECIALTY}.
    --> Instauration de tamsulosine 0,4 mg {DX_NUMERIC} et hydratation en cours.
    --> Protocole lithiase rénale, suivi avec CT de contrôle dans 7 jours.
    --> Avis pris auprès de {NAME_RELATIVE} {DX_ABBREV} {RELATIVE_RELATION}, aucune action nécessaire.
    --> En cas d'anurie ou de pic fébrile : contact immédiat via {TELEFOON}.

    Conseils
    -----
    - Ne plus administrer {DX_DRUG_2} {DX_ABBREV} possible {DX_HOMOGRAPH}
    - Pas d'allergie connue
    - Suivi assuré dans le cadre du parcours {SPECIALTY}
    - {PRONOUN_SUBJ} a reçu des informations sur les chances d'élimination spontanée et la gestion de la douleur

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 08:48
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
    "'X patiente werd gezien...overgeplaatst' / 'zij start met' / '{NAME_RELATIVE} geraadpleegd' -- three gendered-participle traps -> restructured as invariant-noun-subject sentences ('Prise en charge...', 'Instauration de...', 'Avis pris aupres de...').",
]},

{
"template_hash": "b4dd2fbaf899e18a", "letter_type": "opvolgbrief", "specialty": "Pneumologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                  {NAME_RESPONSIBLE}              {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}          ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

    Cher confrère

    UNITÉ : 35106 DATE : {DATE_ENCOUNTER} ORIGINE : inconnue ÂGE :
    {AGE} TAILLE 194,9 cm POIDS : 55,8 kg IMC :
    14,695 TABAGISME : non connu

    Anamnèse :
    ---------
    {DATE_HISTORY} : consultation initiale {DX_ABBREV} {DIAGNOSIS}, plaintes
    de dyspnée à l'effort minime. Aggravation l'hiver dernier,
    symptômes nocturnes fréquents. Pas d'hémoptysie signalée. ATCD {DX_ABBREV}.
    Le {PATIENT_NOUN_GENERIC} a {DX_EPONYM} dans la famille ({RELATIVE_RELATION} :
    {NAME_RELATIVE}), statut post {DX_DRUG}. Depuis {DATE_HISTORY}, légère
    amélioration après le début de {DX_DRUG_2}, mais {HONORIFIC} a encore des difficultés au
    travail. Plus de fièvre depuis la semaine 3/2024. Production d'expectorations diminuée,
    {DX_ABBREV} antibiotiques (azithromycine). {PRONOUN_SUBJ} rapporte de la fatigue et
    une perte de poids de {DX_NUMERIC} kg en 2 mois. Pas de symptômes de thrombose ou
    d'embolie. Déjà exclu via {DX_TEST} dd. {DATE_ENCOUNTER}.
    Anamnèse familiale chargée pour une pathologie pulmonaire {DX_ABBREV} {DX_HOMOGRAPH} ;
    pas de tuberculose connue. Adresse habitée : {TELEFOON}, logement bien
    ventilé, pas de moisissures constatées. Plus de sang en toussant depuis le début
    du traitement. Symptômes réexaminés aux urgences. Antécédents médicaux :
    {DIAGNOSIS} diagnostiqué(e) sur base de
    {DX_TEST}, voir rapport du {DATE_HISTORY}. {PATIENT_NOUN_MARKED} signale parfois
    un essoufflement en parlant, surtout en cas d'agitation émotionnelle. Réveils
    nocturnes {DX_ABBREV} difficultés respiratoires, amélioré en surélevant la tête de lit.
    Aucune réaction allergique jamais signalée, vérifié dans le dossier -> « pas d'allergie
    connue ». Voyage récent vers {DX_CODESWITCH}, aucun problème
    constaté pendant le vol.

    Médication actuelle :
    ------------------
    - {DX_DRUG_2} (comp. 10 mg), 10 mg, {DX_NUMERIC}, {DX_NUMERIC}
    - Seretide (poudre pour inhalation 50/250 mcg), 1 bouffée, {DX_NUMERIC}, le matin et le soir
    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}, SC, jours alternés
    - Paracétamol (comp. 1 g), sur indication, max 3/j
    - Aucun traitement à domicile enregistré en dehors de ce qui précède

    Examens techniques :
    --------------------------
    Spirométrie dd. {DATE_ENCOUNTER} : VEMS {DX_NUMERIC} % de la valeur prédite, rapport VEMS/CVF
    diminué ! Confirme un profil obstructif. Capacité de diffusion (DLCO) : légère
    réduction, à corriger {DX_ABBREV} hémoglobine. RX thorax : image hypertransparente
    à droite, augmentation de volume, parois bronchiques épaissies. CT-thorax :
    bronchectasies bilatérales, apex gauche > base, stabilité par rapport à l'examen précédent.
    Gazométrie : pH 7,40, pO2 9,8 kPa, pCO2 5,2 kPa, {DX_ABBREV} saturation à l'air ambiant. Écho :
    dimensions VD normales, pas d'hypertension pulmonaire mise en évidence.
    Test de marche de 6 minutes : 420 mètres, score de Borg 4 à la fin, dyspnée comme motif principal.
    Microbiologie : culture d'expectorations négative pour bactéries et bacilles acido-résistants, voir
    rapport de laboratoire {DX_CODESWITCH}. Test PCR pour {DX_HOMOGRAPH}
    virus : négatif. Sérologie : IgG positif anti-{DX_ANATOMY}, suggérant
    une infection ancienne.

    Conclusion :
    ---------
    Le {PATIENT_NOUN_GENERIC} a été revu en consultation {SPECIALTY} {DX_ABBREV}
    {DIAGNOSIS}, voir courrier dd. {DATE_HISTORY}. Symptômes
    partiellement stabilisés sous le régime actuel, mais symptômes persistants
    lors des activités quotidiennes. Pas d'infection aiguë présente, cependant
    la composante chronique reste dominante.
    --> Optimisation du traitement envisagée via intensification du traitement inhalé.
    --> Concertation avec la kinésithérapie pour rééducation respiratoire, planification dans 2
    semaines.
    --> Pas d'indication de revalidation pulmonaire pour le moment, à reconsidérer en cas de
    progression.
    Suivi prévu 3 mois après le {DATE_ENCOUNTER} ; en cas d'aggravation, nous contacter plus tôt
    via {TELEFOON}.

    Conseils :
    ------
    - Poursuite du traitement actuel
    - Éviter la fumée, la poussière, les polluants atmosphériques
    - Vérifier le statut vaccinal : vaccination {DX_DRUG_2} en ordre (voir dossier)
    - Surveiller le poids et l'équilibre hydrique
    - Nous contacter en cas d'expectorations récidivantes, de fièvre ou de dyspnée !
    - Conseil de voyage : pas de contre-indication pour les vols courts, cabine pressurisée autorisée

    Examens techniques :
    ---------------------
    Spirométrie, CT-thorax, gazométrie, test de marche de 6 min, culture d'expectorations – tous disponibles
    dans le PACS. Examen de référence dd. {DATE_HISTORY} pour comparaison. Images
    examinées par {NAME_PATIENT}. Le {PATIENT_NOUN_GENERIC} a été informé des résultats, a compris
    le plan et a donné son accord pour la suite du parcours. Un
    défect {DX_ANATOMY} sous-jacent n'est pas à exclure, suivi à long terme nécessaire.
    Notice {DX_DRUG_2} envoyée par e-mail vers
    la plateforme {DX_CODESWITCH}. Valeurs de laboratoire dans les limites, CRP
    légèrement élevée : 8 mg/L ({DX_NUMERIC}).

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}        {NAME_DOCTOR_2}
    {NAME_DOCTOR_3}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 13:52
    ------------------------------------------------------------------
    {STREET}      T {TELEFOON}
    {STREET}      T {TELEFOON}

    {STREET}    T {TELEFOON}
    {STREET}    T {TELEFOON}

    {ORGANIZATION}
    {URL}
""",
"adaptation_notes": [
    "MINOR SOURCE ISSUE FOUND: 'Follow-up gepland op {DATE_ENCOUNTER} + 3 maanden' -- not a broken placeholder (unlike the 910ee8bd5e921c1b bug, the brace syntax here is valid), but confusing style since it renders as '[encounter date] + 3 maanden' rather than the actual follow-up date. Cleaned up to a natural relative-time phrase 'Suivi prevu 3 mois apres le {DATE_ENCOUNTER}' during translation.",
    "OBSERVATION (not fixed, preserved as-is): 'Beelden beoordeeld door {NAME_PATIENT}' ('images reviewed by [[NAME_PATIENT]]') is a semantically odd sentence in the Dutch original -- images are normally reviewed by a doctor, not the patient. Left as literal translation since the entity/slot assignment itself is not a PII-safety issue, just an odd narrative claim already present in the source.",
    "Rule 5 applied twice: 'patiente meldt' -> '{PATIENT_NOUN_MARKED} signale'; 'patient werd opnieuw gezien' -> 'Le {PATIENT_NOUN_GENERIC} a ete revu'.",
]},
]

def main():
    out_path = "translated_templates_fr_batch5.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
