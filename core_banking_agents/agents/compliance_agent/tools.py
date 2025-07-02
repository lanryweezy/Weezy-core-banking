# Tools for Compliance Agent

from langchain.tools import tool
from pydantic import HttpUrl
from typing import Dict, Any, List, Optional, Literal
from datetime import date
import random
import logging

# Assuming schemas might be imported for type hinting if complex objects are passed
from .schemas import EntityType # Example

logger = logging.getLogger(__name__)

# --- Mock Data for Tools ---
MOCK_SANCTIONS_DB = {
    "Viktor 'The Ghost' Rostova": {"list_name": "Global Terror Watchlist X", "reason": "Known arms dealer.", "match_score": 0.98},
    "Elena Petrova (b. 1975-03-10)": {"list_name": "EU Consolidated Sanctions", "reason": "Financial crimes and money laundering.", "match_score": 0.92},
    "ACME Corp Overseas Ltd.": {"list_name": "OFAC SDN List (Entity)", "reason": "Operating in sanctioned jurisdiction.", "match_score": 0.99},
}

MOCK_PEP_DB = { # Politically Exposed Persons
    "Ngozi Okoro (b. 1965-11-20, Nigeria)": {"is_pep": True, "role": "Former Minister of Finance", "country": "NG", "pep_level": "Domestic PEP - High Risk"},
    "John Smith (b. 1972-07-01, USA)": {"is_pep": True, "role": "Senator", "country": "US", "pep_level": "Foreign PEP"},
    "Amaka Adebayo (b. 1980-05-05, Nigeria)": {"is_pep": False} # Example of a non-PEP
}

MOCK_ADVERSE_MEDIA_KEYWORDS = {
    "fraud": ["Bogus Investment Ltd.", "Viktor 'The Ghost' Rostova"],
    "corruption": ["Shady Deals Inc.", "Elena Petrova"],
    "money laundering": ["WashAMillion Services", "Elena Petrova"],
    "terrorism": ["Viktor 'The Ghost' Rostova"]
}


@tool("SanctionsListTool")
def sanctions_list_tool(
    entity_name: str,
    entity_type: EntityType, # Literal["Individual", "Organization"]
    date_of_birth: Optional[str] = None, # YYYY-MM-DD string
    nationality: Optional[str] = None # ISO Alpha-2
) -> Dict[str, Any]:
    """
    Simulates checking an entity against global and local sanctions lists.

    Args:
        entity_name (str): Full name of the individual or organization.
        entity_type (EntityType): "Individual" or "Organization".
        date_of_birth (Optional[str]): Date of birth for individuals (YYYY-MM-DD).
        nationality (Optional[str]): Nationality for individuals.

    Returns:
        Dict[str, Any]: Contains 'status' ("Clear", "Hit", "Error"),
                        and 'hits' (List of hit details if status is "Hit").
    """
    logger.info(f"SanctionsListTool: Screening '{entity_name}' (Type: {entity_type}, DOB: {date_of_birth}, Nat: {nationality})")
    hits = []
    status: Literal["Clear", "Hit", "Error"] = "Clear" # type: ignore

    if "error_sanctions" in entity_name.lower():
        return {"status": "Error", "message": "Simulated error connecting to sanctions screening service."}

    for sanctioned_name, details in MOCK_SANCTIONS_DB.items():
        # Simple substring match for mock. Real systems use fuzzy matching, aliases, etc.
        if entity_name.lower() in sanctioned_name.lower() or sanctioned_name.lower() in entity_name.lower():
            # Basic DOB check for individuals if provided
            if entity_type == "Individual" and date_of_birth:
                if f"(b. {date_of_birth})" in sanctioned_name: # Mock stores DOB in name for easy match
                    hits.append({**details, "matched_on_name": entity_name, "matched_on_dob": date_of_birth})
                    status = "Hit"
                # else: could add logic for name match but DOB mismatch (potential false positive)
            elif entity_type == "Organization":
                 hits.append({**details, "matched_on_name": entity_name})
                 status = "Hit"
            elif entity_type == "Individual" and not date_of_birth: # Name match, no DOB to confirm/deny further for this mock
                 hits.append({**details, "matched_on_name": entity_name, "note": "DOB not provided for stricter matching."})
                 status = "Hit" # Treat as hit, may need review

    if not hits:
        logger.info(f"SanctionsListTool: '{entity_name}' is Clear.")
    else:
        logger.warning(f"SanctionsListTool: '{entity_name}' has Potential Hit(s): {hits}")

    return {"status": status, "hits": hits}


@tool("PEPScreeningTool")
def pep_screening_tool(
    entity_name: str,
    date_of_birth: Optional[str] = None, # YYYY-MM-DD
    nationality: Optional[str] = None,
    country_of_residence: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simulates checking if an entity is a Politically Exposed Person (PEP).

    Args:
        entity_name (str): Full name of the individual.
        date_of_birth (Optional[str]): Date of birth (YYYY-MM-DD).
        nationality (Optional[str]): Nationality.
        country_of_residence (Optional[str]): Country of residence.

    Returns:
        Dict[str, Any]: Contains 'is_pep' (bool) and 'pep_details' (dict if PEP).
    """
    logger.info(f"PEPScreeningTool: Screening '{entity_name}' (DOB: {date_of_birth}, Nat: {nationality}, Res: {country_of_residence}) for PEP status.")

    if "error_pep" in entity_name.lower():
        return {"is_pep": False, "pep_details": None, "error": "Simulated error connecting to PEP database."}

    for pep_entry_name, details in MOCK_PEP_DB.items():
        if entity_name.lower() in pep_entry_name.lower():
            # Mock includes DOB and country in name for easier matching in this simulation
            if date_of_birth and f"(b. {date_of_birth})" in pep_entry_name:
                if details["is_pep"]:
                    logger.warning(f"PEPScreeningTool: '{entity_name}' identified as PEP: {details}")
                    return {"is_pep": True, "pep_details": details}
            elif not date_of_birth and details["is_pep"]: # Name match, no DOB, assume PEP for mock if name is unique enough
                 logger.warning(f"PEPScreeningTool: '{entity_name}' identified as PEP (name match, DOB not used for this mock entry): {details}")
                 return {"is_pep": True, "pep_details": details}


    logger.info(f"PEPScreeningTool: '{entity_name}' is not identified as a PEP in mock DB.")
    return {"is_pep": False, "pep_details": None}


@tool("AdverseMediaTool")
def adverse_media_tool(entity_name: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Simulates searching for adverse media related to an entity.

    Args:
        entity_name (str): Name of the entity to search for.
        keywords (Optional[List[str]]): Specific keywords to include in the search (e.g., "fraud", "bribery").

    Returns:
        Dict[str, Any]: Contains 'media_hits_count', 'summary_of_findings', 'sample_hit_urls'.
    """
    logger.info(f"AdverseMediaTool: Searching for adverse media for '{entity_name}', Keywords: {keywords}")

    if "error_media" in entity_name.lower():
        return {"media_hits_count": 0, "summary_of_findings": None, "sample_hit_urls": [], "error": "Simulated error with media search service."}

    hits_count = 0
    findings_summary_parts: List[str] = []
    sample_urls: List[HttpUrl] = [] # type: ignore

    # Check against predefined keywords and entities known to have adverse media in mock
    search_terms = [entity_name.lower()] + ([kw.lower() for kw in keywords] if keywords else [])

    for category, entities_with_adverse_media in MOCK_ADVERSE_MEDIA_KEYWORDS.items():
        for term in search_terms:
            if any(entity.lower() in term for entity in entities_with_adverse_media) or \
               any(term in entity.lower() for entity in entities_with_adverse_media): # Check if search term is in our list or vice versa
                if category not in findings_summary_parts: # Avoid duplicate category messages
                    findings_summary_parts.append(f"Potential adverse media related to '{category}'.")
                hits_count += random.randint(1,3) # Simulate multiple articles for a hit
                sample_urls.append(HttpUrl(f"https://mocknews.com/search?q={entity_name.replace(' ','+')}+{category}")) # type: ignore
                break # Found for this category, move to next category or term

    if not hits_count:
        summary = "No significant adverse media found in mock search."
        logger.info(f"AdverseMediaTool: {summary} for '{entity_name}'.")
    else:
        summary = " ".join(findings_summary_parts) + f" Found approximately {hits_count} relevant mentions (simulated)."
        logger.warning(f"AdverseMediaTool: Potential adverse media for '{entity_name}'. Summary: {summary}")
        # Ensure unique URLs if multiple keywords hit same mock URL generator
        sample_urls = list(set(sample_urls))


    return {"media_hits_count": hits_count, "summary_of_findings": summary, "sample_hit_urls": sample_urls}


@tool("RegulatoryReportingTool")
def regulatory_reporting_tool(report_type: Literal["SAR", "CTR"], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    (Placeholder) Simulates assisting with or generating regulatory reports like SAR or CTR.
    In a real system, this would involve complex data aggregation, formatting, and possibly submission.

    Args:
        report_type (Literal["SAR", "CTR"]): The type of report to generate.
        data (Dict[str, Any]): Data required for the report (e.g., from SARDataInput schema).

    Returns:
        Dict[str, Any]: Confirmation of report generation/assistance.
    """
    logger.info(f"RegulatoryReportingTool: Received request for {report_type} with data: {str(data)[:200]}...")
    if report_type == "SAR":
        # Mock SAR generation
        report_id = f"MOCK_SAR_{data.get('case_reference_id', random.randint(1000,9999))}"
        message = f"Suspicious Activity Report (SAR) draft generated with ID {report_id}. Ready for MLRO review."
        logger.info(message)
        return {"status": "SAR Drafted", "report_id": report_id, "message": message}
    elif report_type == "CTR":
        report_id = f"MOCK_CTR_{random.randint(1000,9999)}"
        message = f"Currency Transaction Report (CTR) data compiled for submission. Ref: {report_id}."
        logger.info(message)
        return {"status": "CTR Data Compiled", "report_id": report_id, "message": message}

    return {"status": "Error", "message": f"Unsupported report type: {report_type}"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("--- Testing ComplianceAgent Tools ---")

    print("\n1. Testing SanctionsListTool:")
    s_res_clear = sanctions_list_tool.run({"entity_name": "Good Citizen Inc.", "entity_type": "Organization"})
    print(f"  Sanctions (Clear): {s_res_clear}")
    s_res_hit_org = sanctions_list_tool.run({"entity_name": "ACME Corp Overseas Ltd.", "entity_type": "Organization"})
    print(f"  Sanctions (Hit Org): {s_res_hit_org}")
    s_res_hit_ind = sanctions_list_tool.run({"entity_name": "Elena Petrova", "entity_type": "Individual", "date_of_birth": "1975-03-10"})
    print(f"  Sanctions (Hit Ind w/ DOB): {s_res_hit_ind}")
    s_res_hit_ind_no_dob = sanctions_list_tool.run({"entity_name": "Viktor 'The Ghost' Rostova", "entity_type": "Individual"})
    print(f"  Sanctions (Hit Ind no DOB): {s_res_hit_ind_no_dob}")
    s_res_error = sanctions_list_tool.run({"entity_name": "error_sanctions Test", "entity_type": "Organization"})
    print(f"  Sanctions (Error): {s_res_error}")


    print("\n2. Testing PEPScreeningTool:")
    p_res_clear = pep_screening_tool.run({"entity_name": "Amaka Adebayo", "date_of_birth": "1980-05-05", "nationality": "NG"})
    print(f"  PEP (Clear): {p_res_clear}")
    p_res_hit = pep_screening_tool.run({"entity_name": "Ngozi Okoro", "date_of_birth": "1965-11-20", "nationality": "NG"})
    print(f"  PEP (Hit): {p_res_hit}")
    p_res_error = pep_screening_tool.run({"entity_name": "error_pep Test"})
    print(f"  PEP (Error): {p_res_error}")


    print("\n3. Testing AdverseMediaTool:")
    am_res_clear = adverse_media_tool.run({"entity_name": "Clean Sky Ltd."})
    print(f"  Adverse Media (Clear): Hits={am_res_clear['media_hits_count']}, Summary='{am_res_clear['summary_of_findings']}'")
    am_res_hit = adverse_media_tool.run({"entity_name": "Bogus Investment Ltd.", "keywords": ["fraud", "scam"]})
    print(f"  Adverse Media (Hit): Hits={am_res_hit['media_hits_count']}, Summary='{am_res_hit['summary_of_findings']}', URLs: {am_res_hit['sample_hit_urls']}")
    am_res_entity_keyword_hit = adverse_media_tool.run({"entity_name": "Elena Petrova"}) # Elena Petrova is in MOCK_ADVERSE_MEDIA_KEYWORDS
    print(f"  Adverse Media (Entity Keyword Hit): Hits={am_res_entity_keyword_hit['media_hits_count']}, Summary='{am_res_entity_keyword_hit['summary_of_findings']}'")
    am_res_error = adverse_media_tool.run({"entity_name": "error_media Test"})
    print(f"  Adverse Media (Error): {am_res_error}")

    print("\n4. Testing RegulatoryReportingTool (Placeholder):")
    sar_data_example = {"case_reference_id": "CASE001", "narrative": "Suspicious cash deposits."}
    rep_res_sar = regulatory_reporting_tool.run({"report_type": "SAR", "data": sar_data_example})
    print(f"  Regulatory Reporting (SAR): {rep_res_sar}")
    ctr_data_example = {"transaction_id": "TXN999", "amount": 6000000}
    rep_res_ctr = regulatory_reporting_tool.run({"report_type": "CTR", "data": ctr_data_example})
    print(f"  Regulatory Reporting (CTR): {rep_res_ctr}")

    print("\nCompliance Agent tools implemented with mocks.")
