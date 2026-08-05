import re
import logging
from backend.models.schemas import PatientInfo

logger = logging.getLogger(__name__)

def parse_patient_info(ocr_text: str) -> PatientInfo:
    """Extract patient information using regex and structured parsing."""
    info = {
        'name': 'Not Available',
        'age': 'Not Available',
        'gender': 'Not Available',
        'report_date': 'Not Available',
        'lab_name': 'Not Available',
        'ref_number': 'Not Available'
    }
    
    # Name: typically 'Patient Name: John Doe'
    name_match = re.search(r'(?:Patient\s+Name|Name|Pt\.\s*Name)\s*[:\-]\s*([A-Za-z\s]+)', ocr_text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
        if len(name) > 2: info['name'] = name

    # Age
    age_match = re.search(r'(?:Age|DOB|Date of Birth)\s*[:\-]\s*(\d{1,3}\s*(?:Yrs|Years|Y|M)?|\d{2}/\d{2}/\d{4})', ocr_text, re.IGNORECASE)
    if age_match:
        info['age'] = age_match.group(1).strip()

    # Gender
    gender_match = re.search(r'(?:Gender|Sex)\s*[:\-]\s*(Male|Female|M|F|Other)', ocr_text, re.IGNORECASE)
    if gender_match:
        info['gender'] = gender_match.group(1).strip()

    # Report Date
    date_match = re.search(r'(?:Date|Report Date|Collection Date)\s*[:\-]\s*(\d{2}[-/]\d{2}[-/]\d{2,4}|[A-Za-z]{3}\s+\d{1,2},?\s+\d{4})', ocr_text, re.IGNORECASE)
    if date_match:
        info['report_date'] = date_match.group(1).strip()

    # Lab Name
    lab_match = re.search(r'(?:Lab Name|Laboratory|Clinic)\s*[:\-]\s*([A-Za-z\s]+)', ocr_text, re.IGNORECASE)
    if lab_match:
        info['lab_name'] = lab_match.group(1).strip()

    # Ref Number / Patient ID
    ref_match = re.search(r'(?:Ref|Reference|Patient ID|ID|PID)\s*[:\-]\s*([A-Z0-9-]+)', ocr_text, re.IGNORECASE)
    if ref_match:
        info['ref_number'] = ref_match.group(1).strip()

    return PatientInfo(**info)
