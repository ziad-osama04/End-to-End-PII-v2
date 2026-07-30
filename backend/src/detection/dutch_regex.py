from presidio_analyzer import Pattern, PatternRecognizer

def get_dutch_regex_recognizers():
    """Returns a list of PatternRecognizers for leaked PII categories."""
    
    recognizers = []
    
    # 1. Date — matches any dd-mm-yyyy, so labelled DATE (the model's concept),
    #    not DOB: the pattern can't tell a birth date from any other date.
    dob_pattern = Pattern(name="leaked_dob", regex=r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", score=0.6)
    # month-year, e.g. "12-2025" (safe)
    myear = Pattern(name="leaked_month_year", regex=r"\b(?:0?[1-9]|1[0-2])[-/]\d{4}\b", score=0.6)
    dob_recognizer = PatternRecognizer(supported_language='nl',
        supported_entity="DATE",
        patterns=[dob_pattern, myear],
        context=["geboortedatum", "geboren", "dob"]
    )
    recognizers.append(dob_recognizer)

    # 2. Age
    age_pattern = Pattern(name="leaked_age", regex=r"\b\d{1,3}\s*(?:jaar|jr|j\.|-?jarige?)\b", score=0.6)
    age_recognizer = PatternRecognizer(supported_language='nl',
        supported_entity="AGE",
        patterns=[age_pattern], 
        context=["leeftijd", "oud", "man", "vrouw", "patiënt"]
    )
    recognizers.append(age_recognizer)
    
    # 3. Height (Leaked in Doc 2)
    height_pattern = Pattern(name="leaked_height", regex=r"\b\d{2,3}\s*(?:cm|meter|m)\b", score=0.6)
    height_recognizer = PatternRecognizer(supported_language='nl', 
        supported_entity="HEIGHT",
        patterns=[height_pattern], 
        context=["lengte", "lang", "grootte"]
    )
    recognizers.append(height_recognizer)
    
    # 4. Weight (Leaked in Doc 2)
    weight_pattern = Pattern(name="leaked_weight", regex=r"\b\d{2,3}\s*(?:kg|kilo)\b", score=0.6)
    weight_recognizer = PatternRecognizer(supported_language='nl', 
        supported_entity="WEIGHT",
        patterns=[weight_pattern], 
        context=["gewicht", "weegt"]
    )
    recognizers.append(weight_recognizer)
    
    # 5. BMI (Leaked in Doc 2)
    bmi_pattern = Pattern(name="leaked_bmi", regex=r"\bBMI[\s:]*\d{2}[.,]?\d{0,2}\b", score=0.8)
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="BMI", patterns=[bmi_pattern]))
    
    # 6. Race/Ethnicity (Leaked in Doc 2)
    # Using a list of common Dutch/Belgian terms found in medical contexts
    ethnicity_terms = ["caucasisch", "kaukasisch", "blank", "aziatisch", "negroïde", "mediterraan", "arabisch", "hispanic"]
    regex_str = r"\b(?:" + "|".join(ethnicity_terms) + r")\b"
    race_pattern = Pattern(name="leaked_race", regex=regex_str, score=0.6)
    race_recognizer = PatternRecognizer(supported_language='nl', 
        supported_entity="RACE",
        patterns=[race_pattern], 
        context=["ras", "etniciteit", "afkomst"]
    )
    recognizers.append(race_recognizer)
    
    # 7. Department Code (Leaked in Doc 2)
    dept_pattern = Pattern(name="leaked_dept", regex=r"\b[A-Z]{1,4}[-]?\d{1,4}\b", score=0.4)
    dept_recognizer = PatternRecognizer(supported_language='nl', 
        supported_entity="DEPT",
        patterns=[dept_pattern], 
        context=["afdeling", "unit", "kamer", "bed", "zaal"]
    )
    recognizers.append(dept_recognizer)
    
    # 8. Hospital Name (Leaked in all docs)
    hospital_pattern = Pattern(name="leaked_hospital", regex=r"\bAZORG\b", score=0.9)
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="HOSPITAL", patterns=[hospital_pattern]))

    # 9. Standard Belgian INSZ (national identification number)
    insz_pattern = Pattern(name="insz_standard", regex=r"\b\d{2}[.-]?\d{2}[.-]?\d{2}[- ]?\d{3}[.-]?\d{2}\b", score=0.8)
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="NATIONAL_ID", patterns=[insz_pattern]))

    # 9b. Standard Belgian RIZIV (healthcare provider number)
    riziv_pattern = Pattern(name="riziv_standard", regex=r"\b\d{1}[-]?\d{5}[-]?\d{2}[-]?\d{3}\b", score=0.8)
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="PROVIDER_ID", patterns=[riziv_pattern]))

    # 10. Phone (BE/NL)
    phone_pattern = Pattern(name="phone_standard", regex=r"\b(?:0|\+32|\+31)[\s-]?\d[\s-]?\d{6,8}\b", score=0.7)
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="PHONE", patterns=[phone_pattern]))
    
    # 11. Dutch/Belgian IBAN
    iban_pattern = Pattern(name="iban_standard", regex=r"\b(?:NL|BE)\d{2}\s?[A-Z]{4}\s?\d{4}\s?\d{4}\s?\d{0,4}\b", score=0.9)
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="IBAN", patterns=[iban_pattern]))
    
    # 12. Address (Street + Number + optional ZIP and City)
    address_pattern = Pattern(
        name="address_standard", 
        regex=r"\b[A-Z][a-zA-Zëéèï]+(?:\s+[a-zA-Zëéèï]+)*\s*(?:straat|laan|weg|plein|dreef|steenweg|baan)\s+\d{1,4}[a-zA-Z]?(?:,\s*\d{4}\s+[A-Z][a-zA-Zëéèï]+)?\b", 
        score=0.5
    )
    recognizers.append(PatternRecognizer(supported_language='nl', supported_entity="ADDRESS", patterns=[address_pattern]))
    
    return recognizers
