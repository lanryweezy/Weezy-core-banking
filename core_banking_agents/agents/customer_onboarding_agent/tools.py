# Tools for Customer Onboarding Agent

from langchain.tools import tool
from pydantic import HttpUrl # For type hinting if URLs are passed directly to tools
from typing import Optional, Dict, Any
import random
import re # For simple phone number formatting

# --- Mock Data (Simulating NIBSS/NIMC databases) ---
MOCK_BVN_DB = {
    "12345678901": {"bvn": "12345678901", "firstName": "Adewale", "lastName": "Ogunseye", "dateOfBirth": "1990-01-15", "phoneNumber": "08012345678", "registrationDate": "2015-03-10"},
    "11223344556": {"bvn": "11223344556", "firstName": "Bola", "lastName": "Adekunle", "dateOfBirth": "1985-05-20", "phoneNumber": "07098765432", "registrationDate": "2016-07-22"},
    "98765432100": {"bvn": "98765432100", "firstName": "Chinedu", "lastName": "Okoro", "dateOfBirth": "1992-11-03", "phoneNumber": "09000000001", "registrationDate": "2017-01-05"},
    "ERROR_BVN_001": {"error": "Simulated Service Unavailable"}, # For testing error handling
}

MOCK_NIN_DB = {
    "98765432109": {"nin": "98765432109", "firstname": "Adewale", "surname": "Ogunseye", "middlename": "T.", "birthdate": "1990-01-15", "telephoneno": "2348012345678", "gender": "M"},
    "88776655443": {"nin": "88776655443", "firstname": "Bola", "surname": "Adekunle", "middlename": "", "birthdate": "1985-05-20", "telephoneno": "2347098765432", "gender": "F"},
    "77665544332": {"nin": "77665544332", "firstname": "Nonso", "surname": "Eze", "middlename": "C", "birthdate": "1988-08-10", "telephoneno": "2348123456789", "gender": "M"}, # Name mismatch example
    "ERROR_NIN_001": {"error": "Simulated Service Down"}, # For testing error handling
}

# Helper to normalize phone numbers (very basic)
def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    # Remove +234 and ensure it starts with 0
    if phone.startswith("+234"):
        phone = "0" + phone[4:]
    elif phone.startswith("234"):
        phone = "0" + phone[3:]
    return re.sub(r'\D', '', phone) # Remove any non-digits just in case

@tool("NINBVNVerificationTool")
def nin_bvn_verification_tool(
    bvn: Optional[str] = None,
    nin: Optional[str] = None,
    first_name: str = "",
    last_name: str = "",
    date_of_birth: str = "", # Expected format YYYY-MM-DD
    phone_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifies BVN (Bank Verification Number) and/or NIN (National Identification Number)
    against mock NIBSS/NIMC databases. It checks if the provided details (name, DOB, phone)
    match the records associated with the BVN/NIN.

    Args:
        bvn (Optional[str]): The BVN to verify.
        nin (Optional[str]): The NIN to verify.
        first_name (str): Applicant's first name.
        last_name (str): Applicant's last name.
        date_of_birth (str): Applicant's date of birth in YYYY-MM-DD format.
        phone_number (Optional[str]): Applicant's phone number.

    Returns:
        Dict[str, Any]: A dictionary containing verification statuses and details for BVN and NIN.
                        Keys include 'bvn_status', 'bvn_details', 'nin_status', 'nin_details'.
                        Possible statuses: "Verified", "Not Found", "Mismatch", "Error", "NotProvided".
    """
    results = {
        "bvn_status": "NotProvided", "bvn_details": {},
        "nin_status": "NotProvided", "nin_details": {}
    }

    normalized_input_phone = normalize_phone(phone_number)

    # --- BVN Verification ---
    if bvn:
        if bvn == "ERROR_BVN_001": # Simulate service error
            results["bvn_status"] = "Error"
            results["bvn_details"] = {"message": MOCK_BVN_DB[bvn]["error"]}
        elif bvn in MOCK_BVN_DB:
            bvn_record = MOCK_BVN_DB[bvn]
            mismatches = []
            if first_name.lower() != bvn_record["firstName"].lower():
                mismatches.append(f"First name mismatch (Expected: {bvn_record['firstName']}, Got: {first_name})")
            if last_name.lower() != bvn_record["lastName"].lower():
                mismatches.append(f"Last name mismatch (Expected: {bvn_record['lastName']}, Got: {last_name})")
            if date_of_birth != bvn_record["dateOfBirth"]:
                mismatches.append(f"DOB mismatch (Expected: {bvn_record['dateOfBirth']}, Got: {date_of_birth})")

            # Optional: Phone number check can be strict or lenient
            bvn_phone_normalized = normalize_phone(bvn_record.get("phoneNumber"))
            if normalized_input_phone and bvn_phone_normalized and normalized_input_phone != bvn_phone_normalized:
                 mismatches.append(f"Phone number mismatch on BVN (Expected: {bvn_phone_normalized}, Got: {normalized_input_phone}) - this check can be optional")


            if not mismatches:
                results["bvn_status"] = "Verified"
                results["bvn_details"] = {
                    "message": "BVN details successfully matched.",
                    "matched_data": bvn_record
                }
            else:
                results["bvn_status"] = "Mismatch"
                results["bvn_details"] = {
                    "message": "Provided details do not fully match BVN record.",
                    "mismatches": mismatches,
                    "bvn_record_summary": {k:v for k,v in bvn_record.items() if k not in ['error']}
                }
        else:
            results["bvn_status"] = "NotFound"
            results["bvn_details"] = {"message": "BVN not found in mock database."}

    # --- NIN Verification ---
    if nin:
        if nin == "ERROR_NIN_001": # Simulate service error
            results["nin_status"] = "Error"
            results["nin_details"] = {"message": MOCK_NIN_DB[nin]["error"]}
        elif nin in MOCK_NIN_DB:
            nin_record = MOCK_NIN_DB[nin]
            mismatches = []
            if first_name.lower() != nin_record["firstname"].lower():
                mismatches.append(f"First name mismatch (Expected: {nin_record['firstname']}, Got: {first_name})")
            if last_name.lower() != nin_record["surname"].lower():
                mismatches.append(f"Last name mismatch (Expected: {nin_record['surname']}, Got: {last_name})")
            if date_of_birth != nin_record["birthdate"]:
                mismatches.append(f"DOB mismatch (Expected: {nin_record['birthdate']}, Got: {date_of_birth})")

            nin_phone_normalized = normalize_phone(nin_record.get("telephoneno"))
            if normalized_input_phone and nin_phone_normalized and normalized_input_phone != nin_phone_normalized:
                 mismatches.append(f"Phone number mismatch on NIN (Expected: {nin_phone_normalized}, Got: {normalized_input_phone})")

            if not mismatches:
                results["nin_status"] = "Verified"
                results["nin_details"] = {
                    "message": "NIN details successfully matched.",
                    "matched_data": nin_record
                }
            else:
                results["nin_status"] = "Mismatch"
                results["nin_details"] = {
                    "message": "Provided details do not fully match NIN record.",
                    "mismatches": mismatches,
                    "nin_record_summary": {k:v for k,v in nin_record.items() if k not in ['error']}
                }
        else:
            results["nin_status"] = "NotFound"
            results["nin_details"] = {"message": "NIN not found in mock database."}

    return results

# Placeholder for other tools (OCRTool, FaceMatchTool) to be added later.
# @tool("OCRTool")
# ...

# @tool("FaceMatchTool")
# ...

if __name__ == "__main__":
    print("--- Testing NINBVNVerificationTool ---")

    # Test Case 1: BVN Verified
    print("\nTest Case 1: BVN Verified")
    res1 = nin_bvn_verification_tool(bvn="12345678901", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08012345678")
    print(res1)

    # Test Case 2: NIN Verified
    print("\nTest Case 2: NIN Verified")
    res2 = nin_bvn_verification_tool(nin="88776655443", first_name="Bola", last_name="Adekunle", date_of_birth="1985-05-20", phone_number="07098765432")
    print(res2)

    # Test Case 3: BVN Mismatch (name)
    print("\nTest Case 3: BVN Mismatch (name)")
    res3 = nin_bvn_verification_tool(bvn="12345678901", first_name="Adebayo", last_name="Ogunseye", date_of_birth="1990-01-15")
    print(res3)

    # Test Case 4: NIN Mismatch (name)
    print("\nTest Case 4: NIN Mismatch (name)")
    res4 = nin_bvn_verification_tool(nin="77665544332", first_name="Chijioke", last_name="Eze", date_of_birth="1988-08-10") # Correct is Nonso Eze
    print(res4)

    # Test Case 5: BVN Not Found
    print("\nTest Case 5: BVN Not Found")
    res5 = nin_bvn_verification_tool(bvn="00000000000", first_name="Unknown", last_name="Person", date_of_birth="2000-01-01")
    print(res5)

    # Test Case 6: NIN Not Found
    print("\nTest Case 6: NIN Not Found")
    res6 = nin_bvn_verification_tool(nin="00000000000", first_name="Unknown", last_name="Person", date_of_birth="2000-01-01")
    print(res6)

    # Test Case 7: Both BVN and NIN provided and verified
    print("\nTest Case 7: Both BVN and NIN provided and verified")
    res7 = nin_bvn_verification_tool(bvn="11223344556", nin="88776655443", first_name="Bola", last_name="Adekunle", date_of_birth="1985-05-20", phone_number="07098765432")
    print(res7)

    # Test Case 8: BVN Error Simulation
    print("\nTest Case 8: BVN Error Simulation")
    res8 = nin_bvn_verification_tool(bvn="ERROR_BVN_001", first_name="Test", last_name="Error", date_of_birth="1990-01-01")
    print(res8)

    # Test Case 9: NIN Error Simulation
    print("\nTest Case 9: NIN Error Simulation")
    res9 = nin_bvn_verification_tool(nin="ERROR_NIN_001", first_name="Test", last_name="Error", date_of_birth="1990-01-01")
    print(res9)

    # Test Case 10: Only one identifier provided (NIN)
    print("\nTest Case 10: Only NIN provided")
    res10 = nin_bvn_verification_tool(nin="98765432109", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08012345678")
    print(res10)

    # Test Case 11: Phone number variations
    print("\nTest Case 11: Phone number variations (NIN)")
    res11_correct_phone = nin_bvn_verification_tool(nin="98765432109", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="+2348012345678")
    print(f"With +234: {res11_correct_phone['nin_status']}")
    res11_short_phone = nin_bvn_verification_tool(nin="98765432109", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08012345678")
    print(f"With 080: {res11_short_phone['nin_status']}")
    res11_mismatch_phone = nin_bvn_verification_tool(nin="98765432109", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08099999999")
    print(f"Mismatch phone: {res11_mismatch_phone['nin_status']}, Details: {res11_mismatch_phone['nin_details'].get('mismatches')}")


@tool("OCRTool")
def ocr_tool(document_url: HttpUrl, document_type: str) -> Dict[str, Any]:
    """
    Simulates OCR processing for a given document URL and type.
    In a real scenario, this tool would download the document and use an OCR engine
    (e.g., Tesseract, AWS Textract, Google Vision API) to extract text and structured data.

    Args:
        document_url (HttpUrl): The URL of the document to process.
        document_type (str): The type of document (e.g., "NationalID", "DriversLicense",
                             "Passport", "UtilityBill"). This helps in guiding data extraction.

    Returns:
        Dict[str, Any]: A dictionary with 'status' ("Success", "Failed") and 'extracted_data'.
                        'extracted_data' is a mock dictionary of data typically found on the document.
    """
    print(f"OCRTool: Processing document '{document_url}' of type '{document_type}'")
    # Simulate success/failure
    if "error" in str(document_url).lower():
        return {"status": "Failed", "error_message": "Simulated OCR processing error (e.g., unreadable document).", "extracted_data": None}

    mock_data = {"document_url": str(document_url), "document_type": document_type}
    if document_type == "NationalID": # Example for Nigerian National ID Card (NIN slip or card)
        mock_data.update({
            "surname": "Ogunseye" if "ogunseye" in str(document_url).lower() else "Doe",
            "first_name": "Adewale" if "adewale" in str(document_url).lower() else "John",
            "middle_name": "T." if "adewale" in str(document_url).lower() else "",
            "nin": nin if (nin := re.search(r'(\d{11})', str(document_url))) else "1234567890X", # Extract if present in URL for mock
            "date_of_birth": "1990-01-15",
            "gender": "Male",
            "address": "10, Unity Road, Ikeja, Lagos",
            "issue_date": "2021-05-10",
            "expiry_date": "N/A" # if it's a NIN slip
        })
    elif document_type == "DriversLicense":
        mock_data.update({
            "license_no": f"DL{random.randint(10000,99999)}",
            "surname": "Adekunle",
            "first_name": "Bola",
            "date_of_birth": "1985-05-20",
            "issue_date": "2022-01-15",
            "expiry_date": "2027-01-14",
            "categories": "B, C1"
        })
    elif document_type == "Passport": # International Passport
        mock_data.update({
            "passport_no": f"P{random.randint(10000000,99999999)}",
            "surname": "Okoro",
            "given_names": "Chinedu Emeka",
            "nationality": "Nigerian",
            "date_of_birth": "1992-11-03",
            "sex": "M",
            "place_of_birth": "Enugu",
            "date_of_issue": "2020-03-01",
            "date_of_expiry": "2025-02-28",
            "issuing_authority": "Nigerian Immigration Service"
        })
    elif document_type == "UtilityBill": # e.g., Electricity bill (NEPA/PHCN)
        mock_data.update({
            "account_name": "Mr. Adewale Ogunseye",
            "address": "10, Unity Road, Ikeja, Lagos", # Should match address being verified
            "biller": "Ikeja Electric",
            "bill_date": "2023-09-25",
            "due_date": "2023-10-15",
            "amount_due_ngn": random.uniform(3000, 15000)
        })
    else:
        mock_data.update({"raw_text": f"Mock OCR text extracted from {document_type} at {document_url}. Content is generic."})

    return {"status": "Success", "extracted_data": mock_data}


@tool("FaceMatchTool")
def face_match_tool(selfie_url: HttpUrl, id_photo_url: HttpUrl) -> Dict[str, Any]:
    """
    Simulates a face matching process between a selfie and a photo from an ID document.
    In a real scenario, this would use a face recognition service (e.g., AWS Rekognition, Azure Face API, Smile Identity).

    Args:
        selfie_url (HttpUrl): URL of the customer's selfie.
        id_photo_url (HttpUrl): URL of the photo extracted from their ID document (e.g., by OCRTool or a separate step).

    Returns:
        Dict[str, Any]: A dictionary containing 'status', 'is_match' (bool), 'match_score' (float),
                        and 'confidence' (str: "High", "Medium", "Low").
    """
    print(f"FaceMatchTool: Comparing selfie '{selfie_url}' with ID photo '{id_photo_url}'")

    if "error" in str(selfie_url).lower() or "error" in str(id_photo_url).lower():
        return {"status": "Failed", "error_message": "Simulated error processing one of the images.", "is_match": False, "match_score": 0.0, "confidence": "Low"}

    # Simulate varying match scores
    # If names in URLs (purely for mock) suggest a match, give higher score
    score = random.uniform(0.60, 0.98) # Base score
    if any(name in str(selfie_url).lower() for name in ["adewale", "bola", "chinedu"]):
        if any(name in str(id_photo_url).lower() for name in ["adewale", "bola", "chinedu"]):
             if str(selfie_url).split('/')[-1].split('.')[0] == str(id_photo_url).split('/')[-1].split('.')[0]: # crude name match
                 score = random.uniform(0.85, 0.99)

    is_match = score >= 0.75 # Example threshold for a match

    confidence = "Low"
    if score > 0.90:
        confidence = "High"
    elif score > 0.70:
        confidence = "Medium"

    return {
        "status": "Success",
        "is_match": is_match,
        "match_score": round(score, 4),
        "confidence": confidence,
        "message": f"Face match score: {score:.4f}. Confidence: {confidence}. Match: {is_match}."
    }


if __name__ == "__main__":
    print("--- Testing NINBVNVerificationTool ---")
    # (Keep existing NINBVNVerificationTool tests)
    res1 = nin_bvn_verification_tool(bvn="12345678901", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08012345678")
    print(f"NINBVN Test 1: {res1['bvn_status']}")


    print("\n--- Testing OCRTool ---")
    ocr_id_res = ocr_tool(document_url=HttpUrl("http://example.com/docs/ogunseye_national_id.jpg"), document_type="NationalID")
    print(f"OCR NationalID: {ocr_id_res['status']}, Data: {ocr_id_res.get('extracted_data',{}).get('nin')}")

    ocr_bill_res = ocr_tool(document_url=HttpUrl("http://example.com/docs/utility_bill_adewale.pdf"), document_type="UtilityBill")
    print(f"OCR UtilityBill: {ocr_bill_res['status']}, Biller: {ocr_bill_res.get('extracted_data',{}).get('biller')}")

    ocr_error_res = ocr_tool(document_url=HttpUrl("http://example.com/docs/error_document.tiff"), document_type="Passport")
    print(f"OCR Error: {ocr_error_res['status']}, Message: {ocr_error_res.get('error_message')}")

    print("\n--- Testing FaceMatchTool ---")
    face_match_res_good = face_match_tool(selfie_url=HttpUrl("http://example.com/photos/adewale_selfie.jpg"), id_photo_url=HttpUrl("http://example.com/photos/adewale_id_photo.png"))
    print(f"Face Match (Good): {face_match_res_good['status']}, Match: {face_match_res_good['is_match']}, Score: {face_match_res_good['match_score']}")

    face_match_res_poor = face_match_tool(selfie_url=HttpUrl("http://example.com/photos/person_x_selfie.jpg"), id_photo_url=HttpUrl("http://example.com/photos/person_y_id_photo.png"))
    print(f"Face Match (Poor): {face_match_res_poor['status']}, Match: {face_match_res_poor['is_match']}, Score: {face_match_res_poor['match_score']}")

    face_match_error_res = face_match_tool(selfie_url=HttpUrl("http://example.com/photos/error_selfie.jpg"), id_photo_url=HttpUrl("http://example.com/photos/some_id.png"))
    print(f"Face Match (Error): {face_match_error_res['status']}, Message: {face_match_error_res.get('error_message')}")


@tool("AMLScreeningTool")
def aml_screening_tool(full_name: str, date_of_birth: str, nationality: str) -> Dict[str, Any]:
    """
    Simulates an Anti-Money Laundering (AML) screening process for an applicant.
    Checks against mock sanctions lists, Politically Exposed Persons (PEP) lists, and adverse media.

    Args:
        full_name (str): The full name of the applicant.
        date_of_birth (str): The applicant's date of birth (YYYY-MM-DD).
        nationality (str): The applicant's nationality (e.g., "NG" for Nigerian).

    Returns:
        Dict[str, Any]: A dictionary containing the screening result:
                        'status' ("Clear", "Hit", "Error"),
                        'risk_level' ("Low", "Medium", "High"),
                        'details' (e.g., list name if a hit, reasons for risk level).
    """
    print(f"AMLScreeningTool: Screening '{full_name}', DOB: {date_of_birth}, Nationality: {nationality}")

    # Mock data for sanctioned individuals or PEPs
    mock_sanctions_list = {
        "Victor Zakhaev": {"list": "UN Sanctions List", "reason": "Terrorist Financing"},
        "Serena Kogan": {"list": "OFAC SDN List", "reason": "Financial Crimes"},
        "John Doe Politician": {"list": "PEP List", "reason": "Domestic PEP"},
    }
    mock_high_risk_nationalities = ["SYR", "IRN", "PRK"] # Example

    status = "Clear"
    risk_level = "Low"
    details: Dict[str, Any] = {"screened_lists": ["Mock Sanctions", "Mock PEP", "Mock Adverse Media"]}

    if "error_aml" in full_name.lower():
        return {"status": "Error", "risk_level": "Undetermined", "details": {"message": "Simulated AML service connection error."}}

    for name_on_list, info in mock_sanctions_list.items():
        if name_on_list.lower() in full_name.lower():
            status = "Hit"
            risk_level = "High"
            details["hit_details"] = {
                "matched_name": name_on_list,
                "list_name": info["list"],
                "reason": info["reason"]
            }
            details["message"] = f"Applicant matched on {info['list']}."
            break # Stop on first critical hit for this mock

    if status == "Clear" and nationality.upper() in mock_high_risk_nationalities:
        risk_level = "Medium" # Could be High depending on policy
        details["message"] = f"Applicant nationality ({nationality}) is on a high-risk jurisdiction list."
        # Status might remain "Clear" from sanctions, but risk level increases.

    if status == "Clear" and "risky business" in full_name.lower(): # Simulate adverse media hit
        risk_level = "Medium"
        details["adverse_media_hits"] = ["Found negative news related to 'risky business activities'."]
        details["message"] = "Potential adverse media found."


    return {"status": status, "risk_level": risk_level, "details": details}


if __name__ == "__main__":
    print("--- Testing NINBVNVerificationTool ---")
    # (Keep existing NINBVNVerificationTool tests)
    res1 = nin_bvn_verification_tool(bvn="12345678901", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08012345678")
    print(f"NINBVN Test 1: {res1['bvn_status']}")


    print("\n--- Testing OCRTool ---")
    # (Keep existing OCRTool tests)
    ocr_id_res = ocr_tool(document_url=HttpUrl("http://example.com/docs/ogunseye_national_id.jpg"), document_type="NationalID")
    print(f"OCR NationalID: {ocr_id_res['status']}")


    print("\n--- Testing FaceMatchTool ---")
    # (Keep existing FaceMatchTool tests)
    face_match_res_good = face_match_tool(selfie_url=HttpUrl("http://example.com/photos/adewale_selfie.jpg"), id_photo_url=HttpUrl("http://example.com/photos/adewale_id_photo.png"))
    print(f"Face Match (Good): {face_match_res_good['is_match']}")

    print("\n--- Testing AMLScreeningTool ---")
    aml_clear = aml_screening_tool(full_name="Adaobi Chidinma", date_of_birth="1995-03-10", nationality="NG")
    print(f"AML Clear: {aml_clear}")

    aml_hit_sanction = aml_screening_tool(full_name="Mr Victor Zakhaev Badman", date_of_birth="1970-01-01", nationality="RU")
    print(f"AML Hit (Sanction): {aml_hit_sanction}")

    aml_hit_pep = aml_screening_tool(full_name="John Doe Politician", date_of_birth="1965-06-15", nationality="NG")
    print(f"AML Hit (PEP): {aml_hit_pep}")

    aml_high_risk_nation = aml_screening_tool(full_name="Normal Citizen", date_of_birth="1980-02-02", nationality="SYR")
    print(f"AML High Risk Nation: {aml_high_risk_nation}")

    aml_adverse_media = aml_screening_tool(full_name="Risky Business Owner", date_of_birth="1975-12-05", nationality="NG")
    print(f"AML Adverse Media: {aml_adverse_media}")

    aml_error = aml_screening_tool(full_name="Error AML Test", date_of_birth="1990-01-01", nationality="NG")
    print(f"AML Error: {aml_error}")


@tool("DocumentValidationTool")
def document_validation_tool(document_url: HttpUrl, document_type: str, ocr_extracted_data: Dict[str, Any], applicant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Simulates validation of a document's authenticity and consistency with OCR data and applicant details.
    Performs mock checks like format validation, consistency with applicant data, and basic fraud checks.

    Args:
        document_url (HttpUrl): URL of the document.
        document_type (str): Type of the document (e.g., "NationalID", "UtilityBill").
        ocr_extracted_data (Dict[str, Any]): Data extracted by the OCRTool from this document.
        applicant_data (Optional[Dict[str, Any]]): Provided applicant data for cross-referencing
                                                   (e.g., {'first_name': 'Adewale', 'last_name': 'Ogunseye', 'address': '...'}).

    Returns:
        Dict[str, Any]: With 'validation_status' ("Valid", "Suspicious", "Invalid", "Error"),
                        'validation_checks_passed': List[str] of checks that passed.
                        'validation_issues': List[str] of issues found.
    """
    logger.info(f"DocumentValidationTool: Validating doc type '{document_type}' from '{document_url}' with OCR data.")

    status: Literal["Valid", "Suspicious", "Invalid", "Error"] = "Valid" # type: ignore
    checks_passed: List[str] = []
    issues: List[str] = []

    if not ocr_extracted_data or ocr_extracted_data.get("status") == "Failed": # Assuming OCR tool sets a status
        return {"validation_status": "Error", "validation_checks_passed": [], "validation_issues": ["Prerequisite OCR data missing or failed."]}

    # Common checks
    if "mock_tampered_document" in str(document_url):
        issues.append("Document appears to be tampered (simulated).")
        status = "Invalid"
    else:
        checks_passed.append("Basic integrity check (simulated no obvious tampering).")

    # Type-specific checks
    if document_type == "NationalID":
        if ocr_extracted_data.get("nin") and len(ocr_extracted_data.get("nin", "")) == 11:
            checks_passed.append("NIN format appears valid.")
        else:
            issues.append(f"NIN format invalid or missing from OCR: {ocr_extracted_data.get('nin')}")
            status = "Suspicious"
        if applicant_data:
            if ocr_extracted_data.get("first_name","").lower() != applicant_data.get("first_name","").lower():
                issues.append(f"First name on ID ('{ocr_extracted_data.get('first_name')}') does not match applicant ('{applicant_data.get('first_name')}').")
                status = "Suspicious"
            else:
                checks_passed.append("First name on ID matches applicant data.")
            if ocr_extracted_data.get("date_of_birth","") != applicant_data.get("date_of_birth",""):
                issues.append(f"DOB on ID ('{ocr_extracted_data.get('date_of_birth')}') does not match applicant ('{applicant_data.get('date_of_birth')}').")
                status = "Suspicious"
            else:
                checks_passed.append("DOB on ID matches applicant data.")

    elif document_type == "UtilityBill":
        if not ocr_extracted_data.get("address"):
            issues.append("Address not found on utility bill OCR data.")
            status = "Suspicious"
        elif applicant_data and applicant_data.get("street_address"):
            # Simple mock address check: check for street number and a common part of the street name
            applicant_addr_parts = applicant_data.get("street_address","").lower().split()
            ocr_addr_parts = ocr_extracted_data.get("address","").lower().split()
            if not (any(p.isdigit() for p in ocr_addr_parts) and # has a number
                    len(set(applicant_addr_parts) & set(ocr_addr_parts)) > 1): # some common words
                issues.append(f"Address on utility bill ('{ocr_extracted_data.get('address')}') seems inconsistent with applicant's address ('{applicant_data.get('street_address')}').")
                status = "Suspicious"
            else:
                checks_passed.append("Address on utility bill appears consistent with applicant data.")
        else:
            checks_passed.append("Utility bill contains an address (basic check).")

        bill_date_str = ocr_extracted_data.get("bill_date")
        if bill_date_str:
            try:
                bill_date = datetime.strptime(bill_date_str, "%Y-%m-%d").date()
                if (datetime.now().date() - bill_date).days > 180: # e.g., older than ~6 months
                    issues.append(f"Utility bill is too old (Date: {bill_date_str}).")
                    status = "Suspicious"
                else:
                    checks_passed.append("Utility bill date is recent.")
            except ValueError:
                issues.append(f"Could not parse utility bill date: {bill_date_str}.")
                status = "Suspicious"
        else:
            issues.append("Utility bill date missing from OCR.")
            status = "Suspicious"

    if status == "Valid" and issues: # If minor issues were raised but not enough to change status
        status = "Suspicious"

    return {
        "validation_status": status,
        "validation_checks_passed": checks_passed,
        "validation_issues": issues,
        "document_details_validated": {"url": str(document_url), "type": document_type}
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO) # Ensure logger is configured for tool's prints
    print("--- Testing NINBVNVerificationTool ---")
    # (Keep existing NINBVNVerificationTool tests)
    res1 = nin_bvn_verification_tool(bvn="12345678901", first_name="Adewale", last_name="Ogunseye", date_of_birth="1990-01-15", phone_number="08012345678")
    print(f"NINBVN Test 1: {res1['bvn_status']}")


    print("\n--- Testing OCRTool ---")
    # (Keep existing OCRTool tests)
    ocr_id_res_data = {"document_url": "http://example.com/docs/ogunseye_national_id.jpg", "document_type": "NationalID"}
    ocr_id_res = ocr_tool.run(ocr_id_res_data)
    print(f"OCR NationalID: {ocr_id_res['status']}")


    print("\n--- Testing FaceMatchTool ---")
    # (Keep existing FaceMatchTool tests)
    face_match_res_good = face_match_tool(selfie_url=HttpUrl("http://example.com/photos/adewale_selfie.jpg"), id_photo_url=HttpUrl("http://example.com/photos/adewale_id_photo.png"))
    print(f"Face Match (Good): {face_match_res_good['is_match']}")

    print("\n--- Testing AMLScreeningTool ---")
    # (Keep existing AMLScreeningTool tests)
    aml_clear = aml_screening_tool(full_name="Adaobi Chidinma", date_of_birth="1995-03-10", nationality="NG")
    print(f"AML Clear: {aml_clear['status']}")

    print("\n--- Testing DocumentValidationTool ---")
    applicant_sample_data = {"first_name": "Adewale", "last_name": "Ogunseye", "date_of_birth": "1990-01-15", "street_address": "10, Unity Road, Ikeja, Lagos"}

    # Valid ID
    ocr_data_valid_id = {"status": "Success", "first_name": "Adewale", "date_of_birth": "1990-01-15", "nin": "12345678901"}
    val_res_id_good = document_validation_tool.run({
        "document_url": HttpUrl("http://example.com/id_good.jpg"), "document_type": "NationalID",
        "ocr_extracted_data": ocr_data_valid_id, "applicant_data": applicant_sample_data
    })
    print(f"ID Validation (Good): {val_res_id_good['validation_status']}, Issues: {val_res_id_good['validation_issues']}")

    # Suspicious ID (name mismatch)
    ocr_data_mismatch_id = {"status": "Success", "first_name": "Bayo", "date_of_birth": "1990-01-15", "nin": "12345678901"}
    val_res_id_mismatch = document_validation_tool.run({
        "document_url": HttpUrl("http://example.com/id_mismatch.jpg"), "document_type": "NationalID",
        "ocr_extracted_data": ocr_data_mismatch_id, "applicant_data": applicant_sample_data
    })
    print(f"ID Validation (Mismatch): {val_res_id_mismatch['validation_status']}, Issues: {val_res_id_mismatch['validation_issues']}")

    # Valid Utility Bill
    ocr_data_valid_bill = {"status": "Success", "address": "10, Unity Road, Ikeja", "bill_date": datetime.now().strftime("%Y-%m-%d")}
    val_res_bill_good = document_validation_tool.run({
        "document_url": HttpUrl("http://example.com/bill_good.pdf"), "document_type": "UtilityBill",
        "ocr_extracted_data": ocr_data_valid_bill, "applicant_data": applicant_sample_data
    })
    print(f"Utility Bill Validation (Good): {val_res_bill_good['validation_status']}, Issues: {val_res_bill_good['validation_issues']}")

    # Suspicious Utility Bill (old)
    ocr_data_old_bill = {"status": "Success", "address": "10, Unity Road", "bill_date": "2022-01-01"}
    val_res_bill_old = document_validation_tool.run({
        "document_url": HttpUrl("http://example.com/bill_old.pdf"), "document_type": "UtilityBill",
        "ocr_extracted_data": ocr_data_old_bill, "applicant_data": applicant_sample_data
    })
    print(f"Utility Bill Validation (Old): {val_res_bill_old['validation_status']}, Issues: {val_res_bill_old['validation_issues']}")

    # Invalid (tampered)
    val_res_tampered = document_validation_tool.run({
        "document_url": HttpUrl("http://example.com/mock_tampered_document.jpg"), "document_type": "NationalID",
        "ocr_extracted_data": ocr_data_valid_id, "applicant_data": applicant_sample_data
    })
    print(f"Tampered Doc Validation: {val_res_tampered['validation_status']}, Issues: {val_res_tampered['validation_issues']}")


    print("\nCustomer Onboarding Agent tools (NINBVN, OCR, FaceMatch, AMLScreening, DocumentValidation implemented with mocks).")
