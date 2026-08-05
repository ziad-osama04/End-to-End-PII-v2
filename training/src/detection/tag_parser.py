from presidio_analyzer import Pattern, PatternRecognizer

def get_tag_recognizers():
    """Returns a list of PatternRecognizers for existing redaction tags in the HealthOne NOVA PDFs.
    
    CRITICAL: All recognizers must set supported_language="nl" because
    Presidio defaults to "en" and we analyze with language="nl".
    """
    
    recognizers = []
    
    # 1. Patient — matches "PATIËNT A" through "PATIËNT E" (PDF uses accented Ë)
    patient_patterns = [
        Pattern(name="tagged_patient_accent", regex=r"PATI[ËE]NT\s+[A-E]\b", score=1.0),
    ]
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_PATIENT", patterns=patient_patterns,
        supported_language="nl"
    ))
    
    # 2. Responsible — matches "Verantwoordelijke A" (PDF uses mixed case)
    responsible_patterns = [
        Pattern(name="tagged_responsible", regex=r"[Vv]erantwoordelijke\s+[A-E]\b", score=1.0),
    ]
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_RESPONSIBLE", patterns=responsible_patterns,
        supported_language="nl"
    ))
    
    # 3. Doctor — matches "dr. ARTS_A", "dr. ARTS_AB", and standalone "ARTS_A"
    doctor_patterns = [
        Pattern(name="tagged_doctor_full", regex=r"dr\.\s*ARTS_[A-Z]{1,2}\b", score=1.0),
        Pattern(name="tagged_arts_standalone", regex=r"\bARTS_[A-Z]{1,2}\b", score=1.0),
    ]
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_DOCTOR", patterns=doctor_patterns,
        supported_language="nl"
    ))
    
    # 4. INSZ + X-block — matches "INSZXXXXXXXXXXX" (concatenated, no space)
    insz_patterns = [
        Pattern(name="tagged_insz_xblock", regex=r"INSZX{5,}", score=1.0),
        Pattern(name="tagged_insz_standalone", regex=r"\bINSZ\b", score=1.0),
    ]
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_NATIONAL_ID", patterns=insz_patterns,
        supported_language="nl"
    ))
    
    # 5. RIZIV + X-block — matches "RIZIVXXXXXXXXXXX" (concatenated, no space)
    riziv_patterns = [
        Pattern(name="tagged_riziv_xblock", regex=r"RIZIVX{5,}", score=1.0),
        Pattern(name="tagged_riziv_standalone", regex=r"\bRIZIV\b", score=1.0),
    ]
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_PROVIDER_ID", patterns=riziv_patterns,
        supported_language="nl"
    ))
    
    # 6. Name/ID X-Placeholder — matches "XXXXXXXXXXX XXXXXXXXXXX"
    name_id_pattern = Pattern(name="tagged_name_id", regex=r"X{5,}\s+X{5,}", score=1.0)
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_NAME_ID", patterns=[name_id_pattern],
        supported_language="nl"
    ))
    
    # 7. Address Placeholder — matches "[ADRES]"
    address_pattern = Pattern(name="tagged_address", regex=r"\[ADRES\]", score=1.0)
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_ADDRESS", patterns=[address_pattern],
        supported_language="nl"
    ))
    
    # 8. Phone Placeholder — matches "[TELEFOON]"
    phone_pattern = Pattern(name="tagged_phone", regex=r"\[TELEFOON\]", score=1.0)
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_PHONE", patterns=[phone_pattern],
        supported_language="nl"
    ))
    
    # 9. URL Placeholder — matches "[URL]"
    url_pattern = Pattern(name="tagged_url", regex=r"\[URL\]", score=1.0)
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_URL", patterns=[url_pattern],
        supported_language="nl"
    ))
    
    # 10. Hospital name "AZORG" — leaked PII present in all docs
    azorg_pattern = Pattern(name="tagged_hospital", regex=r"\bAZORG\b", score=1.0)
    recognizers.append(PatternRecognizer(
        supported_entity="TAGGED_HOSPITAL", patterns=[azorg_pattern],
        supported_language="nl"
    ))
    
    return recognizers
