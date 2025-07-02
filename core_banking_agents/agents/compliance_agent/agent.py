# LangChain/CrewAI agent logic for Compliance Agent

from typing import Dict, Any, List, Optional
from datetime import datetime, date # date is used by tools
import logging
import json

# Assuming schemas are in the same directory or accessible via path
from .schemas import (
    ScreeningRequest, ScreeningResult, ScreeningHitDetails, EntityToScreen,
    ScreeningCheckType, ScreeningStatus, RiskRating, EntityType
)
# Import the defined tools
from .tools import sanctions_list_tool, pep_screening_tool, adverse_media_tool, regulatory_reporting_tool

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)

# --- Agent Definition (Placeholder for CrewAI) ---
# llm_compliance_officer = FakeListLLM(responses=[
#     "Okay, I will start the entity screening process based on the request.",
#     "Performing Sanctions check...",
#     "Performing PEP check...",
#     "Searching for Adverse Media...",
#     "Consolidating screening results for the entity."
# ])

# compliance_tools = [sanctions_list_tool, pep_screening_tool, adverse_media_tool, regulatory_reporting_tool]

# compliance_officer_agent = Agent(
#     role="AI Compliance Screening Officer",
#     goal="Perform comprehensive compliance screening (Sanctions, PEP, Adverse Media) for individuals and organizations. Consolidate findings and determine an overall risk rating and screening status for each entity.",
#     backstory=(
#         "A diligent AI agent dedicated to upholding the bank's compliance standards by meticulously screening entities against various watchlists and information sources. "
#         "It processes screening requests, invokes specialized tools for each check type, and aggregates the results to provide a clear compliance picture, "
#         "flagging potential risks for further review or action."
#     ),
#     tools=compliance_tools,
#     llm=llm_compliance_officer,
#     verbose=True,
#     allow_delegation=False,
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# def create_entity_screening_tasks(entity_json: str, checks_to_perform_list_str: str) -> List[Task]:
#     tasks = []
#     # entity_data = json.loads(entity_json) # Parse if needed
#     # checks = json.loads(checks_to_perform_list_str) # Parse if needed

#     # Task 1: Sanctions Screening (if requested)
#     # if "Sanctions" in checks:
#     #     sanctions_task = Task(
#     #         description=f"Perform Sanctions screening for entity: '{entity_json}'. Use SanctionsListTool.",
#     #         expected_output="JSON string with sanctions check results: {'status': 'Clear'/'Hit', 'hits': [...]}.",
#     #         agent=compliance_officer_agent, tools=[sanctions_list_tool]
#     #     )
#     #     tasks.append(sanctions_task)

#     # Task 2: PEP Screening (if requested)
#     # if "PEP" in checks:
#     #     pep_task = Task(
#     #         description=f"Perform PEP screening for entity: '{entity_json}'. Use PEPScreeningTool.",
#     #         expected_output="JSON string with PEP check results: {'is_pep': true/false, 'pep_details': {...}}.",
#     #         agent=compliance_officer_agent, tools=[pep_screening_tool]
#     #     )
#     #     tasks.append(pep_task)

#     # Task 3: Adverse Media (if requested)
#     # if "AdverseMedia" in checks:
#     #     adverse_media_task = Task(
#     #         description=f"Perform Adverse Media search for entity: '{entity_json}'. Use AdverseMediaTool.",
#     #         expected_output="JSON string with adverse media results: {'media_hits_count': ..., 'summary_of_findings': ..., 'sample_hit_urls': [...]}.",
#     #         agent=compliance_officer_agent, tools=[adverse_media_tool]
#     #     )
#     #     tasks.append(adverse_media_task)

#     # Task 4: Consolidate Results for this Entity (if multiple checks were done)
#     # if len(tasks) > 0: # Only if actual screening tasks were created
#     #     consolidation_task = Task(
#     #         description=f"Consolidate all screening results (Sanctions, PEP, Adverse Media) for entity: '{entity_json}'. Determine an overall screening status and risk rating.",
#     #         expected_output="JSON string matching the ScreeningResult schema for this single entity.",
#     #         agent=compliance_officer_agent, context_tasks=tasks # Depends on all previous screening tasks for this entity
#     #     )
#     #     tasks.append(consolidation_task) # This would be the task whose output is used
#     return tasks


# --- Main Workflow Function (Direct Tool Usage for now, to be replaced by CrewAI kickoff) ---

async def start_entity_screening_workflow_async(request: ScreeningRequest) -> List[Dict[str, Any]]:
    """
    Simulates the entity screening workflow by directly calling tools for each entity.
    This will eventually be replaced by CrewAI agent execution, likely processing one entity at a time
    or having a master agent delegate per-entity screening to sub-agents/tasks.

    Args:
        request (ScreeningRequest): The screening request containing entities and checks to perform.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each aligning with the ScreeningResult schema
                              for one of the screened entities.
    """
    logger.info(f"Agent: Starting entity screening workflow for request ID: {request.request_id} with {len(request.entities_to_screen)} entities.")

    all_entity_results: List[Dict[str, Any]] = []

    for entity_to_screen in request.entities_to_screen:
        logger.info(f"Agent: Processing entity ID '{entity_to_screen.entity_id}', Name: '{entity_to_screen.name}'")

        entity_hits: List[Dict[str, Any]] = [] # For ScreeningHitDetails structure
        entity_errors: List[str] = []
        current_screening_status: ScreeningStatus = "Clear" # type: ignore
        current_risk_rating: RiskRating = "Low" # type: ignore
        summary_messages: List[str] = []

        # Convert Pydantic date to string for tool if tool expects string
        dob_str = entity_to_screen.date_of_birth.isoformat() if entity_to_screen.date_of_birth else None

        if "Sanctions" in request.checks_to_perform:
            logger.debug(f"  Calling SanctionsListTool for '{entity_to_screen.name}'")
            s_result = sanctions_list_tool.run({
                "entity_name": entity_to_screen.name, "entity_type": entity_to_screen.entity_type,
                "date_of_birth": dob_str, "nationality": entity_to_screen.nationality
            })
            if s_result.get("status") == "Hit" and s_result.get("hits"):
                current_screening_status = "ConfirmedHit" # type: ignore
                current_risk_rating = "Critical" # type: ignore
                entity_hits.extend(s_result["hits"])
                summary_messages.append(f"Sanctions Hit: Matched on {s_result['hits'][0]['list_name']}.")
            elif s_result.get("status") == "Error":
                entity_errors.append(f"Sanctions check error: {s_result.get('message', 'Unknown error')}")
                if current_screening_status != "ConfirmedHit": current_screening_status = "Error" # type: ignore
            else: # Clear
                 summary_messages.append("Sanctions: Clear.")


        if "PEP" in request.checks_to_perform and entity_to_screen.entity_type == "Individual":
            logger.debug(f"  Calling PEPScreeningTool for '{entity_to_screen.name}'")
            p_result = pep_screening_tool.run({
                "entity_name": entity_to_screen.name, "date_of_birth": dob_str,
                "nationality": entity_to_screen.nationality,
                "country_of_residence": entity_to_screen.addresses[0] if entity_to_screen.addresses else None # Simplified
            })
            if p_result.get("is_pep"):
                if current_screening_status not in ["ConfirmedHit", "Error"]: current_screening_status = "PotentialHit" # type: ignore
                if current_risk_rating not in ["Critical", "High"]: current_risk_rating = "High" # type: ignore

                pep_hit_detail = { # Constructing a ScreeningHitDetails like object
                    "list_name": "PEP Database (Mock)",
                    "matched_name": entity_to_screen.name,
                    "hit_reason": f"Identified as PEP. Role: {p_result.get('pep_details',{}).get('role')}, Country: {p_result.get('pep_details',{}).get('country')}",
                    "additional_match_info": p_result.get("pep_details")
                }
                entity_hits.append(pep_hit_detail)
                summary_messages.append(f"PEP Status: Identified as PEP - {p_result.get('pep_details',{}).get('pep_level', 'Details unavailable')}.")
            elif p_result.get("error"):
                entity_errors.append(f"PEP check error: {p_result.get('error')}")
                if current_screening_status not in ["ConfirmedHit", "Error"]: current_screening_status = "Error" # type: ignore
            else:
                summary_messages.append("PEP Status: Not identified as PEP.")


        if "AdverseMedia" in request.checks_to_perform:
            logger.debug(f"  Calling AdverseMediaTool for '{entity_to_screen.name}'")
            am_result = adverse_media_tool.run({"entity_name": entity_to_screen.name}) # Keywords can be added
            if am_result.get("media_hits_count", 0) > 0:
                if current_screening_status not in ["ConfirmedHit", "Error"]: current_screening_status = "PotentialHit" # type: ignore
                if current_risk_rating not in ["Critical", "High"]: current_risk_rating = "Medium" # type: ignore

                adverse_hit_detail = {
                     "list_name": "Adverse Media Search (Mock)",
                     "matched_name": entity_to_screen.name, # Or specific finding
                     "hit_reason": am_result.get('summary_of_findings'),
                     "sample_urls": am_result.get('sample_hit_urls')
                }
                # entity_hits.append(adverse_hit_detail) # Decided to put in summary_message for this mock
                summary_messages.append(f"Adverse Media: {am_result.get('summary_of_findings')}")
            elif am_result.get("error"):
                entity_errors.append(f"Adverse Media check error: {am_result.get('error')}")
                if current_screening_status not in ["ConfirmedHit", "Error"]: current_screening_status = "Error" # type: ignore
            else:
                summary_messages.append("Adverse Media: No significant findings.")

        # Final consolidation for this entity
        final_summary_message = " | ".join(summary_messages) if summary_messages else "Screening performed."
        if entity_errors and current_screening_status != "ConfirmedHit": # If not already a critical hit, and errors occurred
            current_screening_status = "Error" # type: ignore
            final_summary_message = "Errors occurred during screening. " + final_summary_message

        # If no hits and no errors, but status became PotentialHit (e.g. from PEP without critical sanction)
        if not entity_hits and not entity_errors and current_screening_status == "PotentialHit":
             if current_risk_rating == "Low": current_risk_rating = "Medium" # type: ignore # e.g. low-risk PEP

        entity_result_dict = {
            "entity_id": entity_to_screen.entity_id,
            "input_name": entity_to_screen.name,
            "screening_status": current_screening_status,
            "overall_risk_rating": current_risk_rating,
            "hits": entity_hits if entity_hits else None,
            "errors": entity_errors if entity_errors else None,
            "summary_message": final_summary_message,
            "last_checked_at": datetime.utcnow().isoformat() # Convert to string for JSON
        }
        all_entity_results.append(entity_result_dict)

    logger.info(f"Agent: Entity screening workflow completed for request ID: {request.request_id}. Processed {len(all_entity_results)} entities.")
    return all_entity_results


if __name__ == "__main__":
    import asyncio

    async def test_compliance_screening_workflow():
        print("--- Testing Compliance Agent Screening Workflow (Direct Tool Usage) ---")

        sample_entities = [
            EntityToScreen(entity_type="Individual", name="Good Man Clem", date_of_birth=date(1990,5,5), nationality="NG"),
            EntityToScreen(entity_type="Individual", name="Elena Petrova", date_of_birth=date(1975,3,10), nationality="RU", aliases=["Lena P."]),
            EntityToScreen(entity_type="Organization", name="ACME Corp Overseas Ltd.", country_of_incorporation="BS"), # Bahamas
            EntityToScreen(entity_type="Individual", name="Ngozi Okoro", date_of_birth=date(1965,11,20), nationality="NG", addresses=["Abuja, Nigeria"]),
            EntityToScreen(entity_type="Organization", name="Shady Deals Inc. error_media"), # Test adverse media error
        ]

        screening_req = ScreeningRequest(
            entities_to_screen=sample_entities,
            checks_to_perform=["Sanctions", "PEP", "AdverseMedia"]
        )

        print(f"\nTesting with Screening Request ID: {screening_req.request_id}")
        screening_results_list = await start_entity_screening_workflow_async(screening_req)

        print("\n--- Final Screening Results from Agent Workflow ---")
        # Print each result, then try to parse with Pydantic schema for validation
        for i, result_dict in enumerate(screening_results_list):
            print(f"\nResult for Entity {i+1} ('{result_dict['input_name']}'):")
            print(json.dumps(result_dict, indent=2, default=str))
            try:
                ScreeningResult(**result_dict) # Validate against schema
                print(f"  (Schema validation successful for entity {result_dict['input_name']})")
            except Exception as e:
                print(f"  (SCHEMA VALIDATION FAILED for entity {result_dict['input_name']}: {e})")


    # asyncio.run(test_compliance_screening_workflow())
    print("Compliance Agent logic (agent.py). Contains workflow to screen entities using tools (mocked execution).")
