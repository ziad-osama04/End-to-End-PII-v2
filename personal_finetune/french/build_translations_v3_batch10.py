# -*- coding: utf-8 -*-
"""Batch 10 (final): the last template, ccf9c6e53a951296."""
import json

TEMPLATES = [
{
"template_hash": "ccf9c6e53a951296", "letter_type": "spoedverslag", "specialty": "Cardiologie",
"masked_text_fr": """COURRIER

PATIENT :                      RESPONSABLE :            DATE :
{NAME_PATIENT}                {NAME_RESPONSIBLE}                 {DATE_ENCOUNTER} 02:00
INSZ{INSZ}              RIZIV{RIZIV}             ENVOYÉ PAR :
                                                            {NAME_DOCTOR_SENDER}

Contenu du rapport
    {ORGANIZATION}
    {SPECIALTY}

 Le {PATIENT_NOUN_GENERIC} susmentionné a été vu au service de {SPECIALTY} le {DATE_ENCOUNTER}. Anamnèse : ---------- {DATE_HISTORY} : {DIAGNOSIS} 02/2022 : {DX_EPONYM} ! Depuis {DATE_HISTORY}, douleur thoracique à l'effort, irradiant vers la gauche. Aggravation la semaine dernière, désormais également douleur au repos. Pas de dyspnée, pas d'orthopnée. Pas de palpitations rapportées. {DX_HOMOGRAPH} initié chez le médecin traitant, sans hospitalisation. ATCD {DX_ABBREV} {DX_ABBREV}. Pas de thrombose ni de {DX_CODESWITCH} dans les antécédents. Médication actuelle : ----------------- - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 comp, {DX_NUMERIC}, {DX_NUMERIC} 20h - {DX_DRUG_2}, 2,5 mg, {DX_NUMERIC} Aucun traitement à domicile enregistré Examens techniques : ------------------------ ECG : {DX_TEST} le {DATE_ENCOUNTER}. Sous-décalage inférieur, inversion de l'onde T latérale. Écho : {DX_ANATOMY} diminuée, FE {DX_NUMERIC}%. Pression télédiastolique augmentée. Troponine : ↑ TA : 146/68x au-dessus de la LSN. Cr : {DX_NUMERIC}, DFGe {DX_NUMERIC}. Après 6h de surveillance : douleur toujours présente pendant {DX_CODESWITCH}. Conclusion : -------- Prise en charge aux urgences pour angor instable chez {PATIENT_NOUN_MARKED} {AGE_ADJ}. Symptômes depuis {DATE_HISTORY}, aggravés. Pas d'instabilité hémodynamique. Le LDL-c est à {DX_NUMERIC}, bien régulé. Anamnèse sociale : {NAME_RELATIVE} ({RELATIVE_RELATION}), domicile au {TELEFOON}. Pas d'allergie connue. Conseils : ------- --> admission en unité d'observation {SPECIALTY} --> arrêt de {DX_DRUG_2} {DX_ABBREV} {DX_HOMOGRAPH} --> instauration de sodium sous-cutané, objectif : stabilisation des symptômes --> consultation cardiologie pour discussion {DX_ABBREV} {DX_DRUG_2} ou CAV Examens techniques : ----------------------- Coronarographie planifiée le lendemain du {DATE_ENCOUNTER}. CT-thorax sans anomalie {DX_EPONYM} ou {DX_ANATOMY}. Prolactinémie {DX_NUMERIC} (voir {DX_TEST}). {DX_ABBREV} sérique {DX_NUMERIC} mmol/L, {DX_NUMERIC} mg/dL. Suivi {SPECIALTY} 7 jours après le {DATE_ENCOUNTER}. Information transmise à {HONORIFIC} {NAME_PATIENT} sur les effets secondaires de {DX_DRUG_2}. Si besoin {DX_ABBREV} {DX_CODESWITCH} dans le passé. {PRONOUN_SUBJ} montre une bonne compréhension du traitement. Dernier contrôle : {DATE_ENCOUNTER} – symptômes en régression. {DX_NUMERIC} jours après {DX_TEST}, pas de récidive. {DX_DRUG_2} sous-cutané poursuivi avec {DX_DRUG_2}. Effet secondaire : {DX_HOMOGRAPH} au site d'injection. {DX_CODESWITCH} plus présent depuis {DATE_HISTORY}. {PRONOUN_SUBJ} signale de la fatigue à l'effort minime. {DX_TEST} négatif pour {DX_ANATOMY}. Dose de {DX_DRUG_2} ajustée sur base de {DX_NUMERIC}. Pas d'indication pour {DX_EPONYM} pour le moment. Consultation {SPECIALTY} {DX_ABBREV} {DX_ABBREV}. {PRONOUN_SUBJ} débute {DX_DRUG_2} per os. {DX_NUMERIC} jours d'observation terminés sans incident. {DX_HOMOGRAPH} stable à l'écho. {DX_TEST} répété : pas de nouvelle anomalie {DX_ANATOMY}. Réorientation vers le médecin traitant. {TELEFOON} correctement renseigné dans le dossier. {PRONOUN_SUBJ} reçoit des informations sur {DX_CODESWITCH}. Effets secondaires de {DX_DRUG_2} documentés. {DX_NUMERIC} mg de {DX_DRUG_2} injectés. {DX_TEST} réalisé le {DATE_ENCOUNTER}. {DX_ABBREV} suivi sur {DX_NUMERIC} mois. {PRONOUN_SUBJ} débute la revalidation via {SPECIALTY}. {NAME_PATIENT} et {NAME_RELATIVE} informés. {HONORIFIC} évoque une possible interaction avec {DX_DRUG_2}. {DX_EPONYM} exclu sur base de {DX_TEST}. {DX_NUMERIC} semaines après {DX_ANATOMY}, plus de symptômes. Sortie envisagée. {DX_HOMOGRAPH} sous contrôle. {SPECIALTY} rapporte sur {DX_CODESWITCH}. {PRONOUN_SUBJ} montre un comportement {AGE_ADJ}. {DX_DRUG_2} remplacé par {DX_DRUG_2}. {DX_NUMERIC} jours d'observation. {PRONOUN_SUBJ} signale une amélioration. {DX_TEST} répété le {DATE_ENCOUNTER}. {DX_ABBREV} stable. {DX_CODESWITCH} absent. Suivi envisagé.

    Bien confraternellement
    {NAME_DOCTOR}
    {SPECIALTY}


    Cordialement, également au nom de
    {NAME_DOCTOR}
    {NAME_DOCTOR_2}

    Ce rapport a été validé électroniquement par {NAME_DOCTOR} le
    {DATE_VALIDATION}

    Validation : {DATE_VALIDATION} 15:58
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
    "Largest/densest template in the set (44 scored spans, 83 extra fields recovered, 10 PRONOUN_SUBJ occurrences) -- a deliberately telegraphic run-on paragraph, likely multiple compressed visit notes concatenated. Preserved the terse, disjointed register rather than smoothing it into full prose, matching the Dutch source's own style.",
    "Cleaned up two valid-but-confusing date-arithmetic patterns (same class as the b4dd2fbaf899e18a fix, not broken placeholders but misleading style): '{DATE_ENCOUNTER} +1' -> 'le lendemain du {DATE_ENCOUNTER}'; '{DATE_ENCOUNTER} +7 dagen' -> '7 jours apres le {DATE_ENCOUNTER}'.",
    "Six separate gendered-participle traps across the run-on paragraph ('werd gezien', 'woonachtig', 'informeerd', 'terugverwezen', 'klaar voor ontslag' x2) -- each restructured with an invariant-noun-as-subject sentence ('Prise en charge...', 'domicile au...', 'Information transmise a...', 'Reorientation vers...', 'Sortie envisagee.', 'Suivi envisage.'), consistent with the fix pattern used throughout this project.",
    "'zij toont {AGE_ADJ} gedrag' is a semantically odd sentence already in the Dutch source (an age-descriptor adjective used as if describing behavior) -- preserved literally as '{PRONOUN_SUBJ} montre un comportement {AGE_ADJ}' rather than reinterpreted, consistent with how the 'Beelden beoordeeld door {NAME_PATIENT}' oddity was handled in b4dd2fbaf899e18a.",
]},
]

def main():
    out_path = "translated_templates_fr_batch10.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} templates -> {out_path}")

if __name__ == "__main__":
    main()
