# LangChain/CrewAI agent logic for Compliance Agent

from typing import Dict, Any, List, Optional
from datetime import datetime, date
import logging
import json

from .schemas import (
    ScreeningRequest, ScreeningResult, ScreeningHitDetails, EntityToScreen,
    ScreeningCheckType, ScreeningStatus, RiskRating, EntityType
)
from .tools import sanctions_list_tool, pep_screening_tool, adverse_media_tool, regulatory_reporting_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- LLM Configuration (Mocked for CrewAI) ---
# Responses for multiple entities and multiple checks per entity + consolidation.
# Each entity might involve ~4 LLM "steps": Sanctions, PEP, AdverseMedia, Consolidate.
mock_llm_compliance_responses = [
    "Okay, I will start the entity screening process for this entity based on the requested checks.", # General start
    "Performing Sanctions check using SanctionsListTool.", # Sanctions task
    "Sanctions check complete. Now performing PEP check using PEPScreeningTool.", # PEP task
    "PEP check complete. Now searching for Adverse Media using AdverseMediaTool.", # Adverse Media task
    "All checks for this entity complete. Consolidating results into a ScreeningResult structure." # Consolidation task
] * 5 # Multiply to cover a few entities and some buffer
llm_compliance_officer = FakeListLLM(responses=mock_llm_compliance_responses)

# --- Agent Definition ---
compliance_tools = [sanctions_list_tool, pep_screening_tool, adverse_media_tool, regulatory_reporting_tool]

compliance_officer_agent = Agent(
    role="AI Compliance Screening Officer",
    goal="Perform comprehensive compliance screening (Sanctions, PEP, Adverse Media) for individuals and organizations. Consolidate findings and determine an overall risk rating and screening status for each entity.",
    backstory=(
        "A diligent AI agent dedicated to upholding the bank's compliance standards by meticulously screening entities against various watchlists and information sources. "
        "It processes screening requests, invokes specialized tools for each check type, and aggregates the results to provide a clear compliance picture, "
        "flagging potential risks for further review or action."
    ),
    tools=compliance_tools,
    llm=llm_compliance_officer,
    verbose=1,
    allow_delegation=False,
)

# --- Task Definitions for CrewAI (for a single entity) ---
def create_entity_screening_tasks(entity_to_screen_dict: Dict[str, Any], checks_to_perform: List[ScreeningCheckType]) -> List[Task]:
    """
    Creates a list of CrewAI tasks to screen a single entity based on requested checks.
    """
    tasks: List[Task] = []
    entity_json_str = json.dumps(entity_to_screen_dict) # For use in task descriptions

    # Store task outputs by name to pass as context if needed (though CrewAI handles this for sequential tasks)
    # For this structure, the consolidation task will rely on the implicit context passing of CrewAI.

    # Sanctions Screening Task
    if "Sanctions" in checks_to_perform:
        sanctions_task = Task(
            description=f"Perform Sanctions screening for the entity detailed in this JSON string: '{entity_json_str}'. Use the SanctionsListTool. Provide all details from the tool's output.",
            expected_output="A JSON string from the SanctionsListTool: {'status': 'Clear'/'Hit', 'hits': [...]}.",
            agent=compliance_officer_agent,
        )
        tasks.append(sanctions_task)

    # PEP Screening Task
    if "PEP" in checks_to_perform and entity_to_screen_dict.get("entity_type") == "Individual":
        pep_task = Task(
            description=f"Perform PEP screening for the entity: '{entity_json_str}'. Use the PEPScreeningTool. Provide all details from the tool's output.",
            expected_output="A JSON string from the PEPScreeningTool: {'is_pep': true/false, 'pep_details': {...}}.",
            agent=compliance_officer_agent,
        )
        tasks.append(pep_task)

    # Adverse Media Task
    if "AdverseMedia" in checks_to_perform:
        adverse_media_task = Task(
            description=f"Perform Adverse Media search for the entity: '{entity_json_str}'. Use the AdverseMediaTool. Provide all details from the tool's output.",
            expected_output="A JSON string from the AdverseMediaTool: {'media_hits_count': ..., 'summary_of_findings': ..., 'sample_hit_urls': [...]}.",
            agent=compliance_officer_agent,
        )
        tasks.append(adverse_media_task)

    # Consolidation Task (Only if other screening tasks were generated)
    if tasks: # If any screening tasks were actually added
        consolidation_task = Task(
            description=f"""\
            Consolidate all screening results (from previous tasks like Sanctions, PEP, Adverse Media) for the entity: '{entity_json_str}'.
            Determine an overall 'screening_status' (e.g., 'Clear', 'PotentialHit', 'ConfirmedHit', 'Error').
            Determine an 'overall_risk_rating' (e.g., 'Low', 'Medium', 'High', 'Critical').
            Compile any 'hits' from individual checks into a list.
            Formulate a 'summary_message'.
            The output MUST be a single JSON string that includes:
            'entity_id', 'input_name', 'screening_status', 'overall_risk_rating', 'hits' (list), 'errors' (list), 'summary_message', 'last_checked_at'.
            This structure should align with the ScreeningResult schema.
            Example for a clear result:
            '{{"entity_id": "{entity_to_screen_dict['entity_id']}", "input_name": "{entity_to_screen_dict['name']}", "screening_status": "Clear", "overall_risk_rating": "Low", "hits": null, "errors": null, "summary_message": "Screening complete, no adverse findings.", "last_checked_at": "YYYY-MM-DDTHH:MM:SSZ"}}'
            Example for a hit:
            '{{"entity_id": "{entity_to_screen_dict['entity_id']}", "input_name": "{entity_to_screen_dict['name']}", "screening_status": "ConfirmedHit", "overall_risk_rating": "Critical", "hits": [{{"list_name": "...", ...}}], "errors": null, "summary_message": "Sanctions Hit found.", "last_checked_at": "YYYY-MM-DDTHH:MM:SSZ"}}'
            """,
            expected_output="A single JSON string structured like the ScreeningResult schema, summarizing all checks for THIS ONE ENTITY.",
            agent=compliance_officer_agent,
            context_tasks=tasks.copy() # Depends on all previously added screening tasks for this entity
        )
        # Replace the individual tasks with just the consolidation task if we want only its output.
        # Or, the crew runs all, and we take the output of the last one (consolidation_task).
        # For this setup, the final task in the list will be the consolidation task.
        tasks.append(consolidation_task)

    return tasks


# --- Main Workflow Function (Now using CrewAI per entity) ---

async def start_entity_screening_workflow_async(request: ScreeningRequest) -> List[Dict[str, Any]]:
    """
    Processes a screening request by creating and running a CrewAI workflow for each entity.
    """
    logger.info(f"Agent (CrewAI): Starting entity screening workflow for request ID: {request.request_id} with {len(request.entities_to_screen)} entities.")

    all_entity_results_dicts: List[Dict[str, Any]] = []

    for entity_to_screen in request.entities_to_screen:
        logger.info(f"Agent (CrewAI): Processing entity ID '{entity_to_screen.entity_id}', Name: '{entity_to_screen.name}'")

        entity_dict_for_crew = entity_to_screen.model_dump(mode='json') # Ensure dates are strings etc.

        # Create tasks specifically for this entity and the requested checks
        entity_specific_tasks = create_entity_screening_tasks(entity_dict_for_crew, request.checks_to_perform)

        if not entity_specific_tasks or not any(task.agent for task in entity_specific_tasks): # Basic check
            logger.error(f"Agent (CrewAI): No valid tasks generated for entity '{entity_to_screen.name}'. Skipping.")
            all_entity_results_dicts.append({
                "entity_id": entity_to_screen.entity_id, "input_name": entity_to_screen.name,
                "screening_status": "Error", "summary_message": "Agent failed to create screening tasks.",
                "last_checked_at": datetime.utcnow().isoformat()
            })
            continue

        entity_crew = Crew(
            agents=[compliance_officer_agent],
            tasks=entity_specific_tasks,
            process=Process.sequential, # Ensure tasks run in order for context passing
            verbose=0 # Keep it less noisy for per-entity runs, can be increased for debugging
        )

        # Inputs for the first task(s). The task descriptions interpolate specific details.
        # The main input here is the entity itself as a JSON string for the tasks to reference.
        crew_inputs = {'entity_json_str': json.dumps(entity_dict_for_crew)}

        # --- ACTUAL CREWAI KICKOFF (Commented out for pure mock) ---
        # logger.info(f"Agent (CrewAI): Kicking off crew for entity '{entity_to_screen.name}'. Inputs: {list(crew_inputs.keys())}")
        # try:
        #     # The result of kickoff is the output of the LAST task in the sequence (consolidation_task)
        #     crew_result_str = entity_crew.kickoff(inputs=crew_inputs)
        #     logger.info(f"Agent (CrewAI): Crew raw result for entity '{entity_to_screen.name}': {crew_result_str[:300]}...")
        # except Exception as e:
        #     logger.error(f"Agent (CrewAI): Crew kickoff failed for entity '{entity_to_screen.name}': {e}", exc_info=True)
        #     crew_result_str = json.dumps({
        #         "entity_id": entity_to_screen.entity_id, "input_name": entity_to_screen.name,
        #         "screening_status": "Error", "summary_message": f"Agent workflow execution error: {str(e)}",
        #         "last_checked_at": datetime.utcnow().isoformat()
        #     })
        # --- END ACTUAL CREWAI KICKOFF ---

        # --- MOCKING CREW EXECUTION (Simulating the consolidation task's output string) ---
        if True: # Keep this block for controlled mocking
            logger.warning(f"Agent (CrewAI): Using MOCKED CrewAI execution path for entity '{entity_to_screen.name}'.")
            # Simulate running tools and the consolidation logic of the final task
            mock_consolidated_result = _simulate_single_entity_consolidation(entity_to_screen, request.checks_to_perform)
            crew_result_str = json.dumps(mock_consolidated_result)
            logger.info(f"Agent (CrewAI): Mocked final JSON output for entity '{entity_to_screen.name}': {crew_result_str[:300]}...")
        # --- END MOCKING CREW EXECUTION ---

        try:
            single_entity_result_dict = json.loads(crew_result_str)
            # Ensure required fields for ScreeningResult are present, or add them
            single_entity_result_dict.setdefault("entity_id", entity_to_screen.entity_id)
            single_entity_result_dict.setdefault("input_name", entity_to_screen.name)
            single_entity_result_dict.setdefault("last_checked_at", datetime.utcnow().isoformat())

            all_entity_results_dicts.append(single_entity_result_dict)
        except json.JSONDecodeError:
            logger.error(f"Agent (CrewAI): Error decoding JSON result for entity '{entity_to_screen.name}': {crew_result_str}", exc_info=True)
            all_entity_results_dicts.append({
                "entity_id": entity_to_screen.entity_id, "input_name": entity_to_screen.name,
                "screening_status": "Error", "summary_message": "Agent returned malformed result (not JSON).",
                "last_checked_at": datetime.utcnow().isoformat()
            })
        except TypeError: # If crew_result_str is None
            logger.error(f"Agent (CrewAI): Crew returned None or non-string result for entity '{entity_to_screen.name}'.", exc_info=True)
            all_entity_results_dicts.append({
                "entity_id": entity_to_screen.entity_id, "input_name": entity_to_screen.name,
                "screening_status": "Error", "summary_message": "Agent workflow returned unexpected data type.",
                "last_checked_at": datetime.utcnow().isoformat()
            })


    logger.info(f"Agent (CrewAI): Entity screening workflow completed for request ID: {request.request_id}. Processed {len(all_entity_results_dicts)} entities.")
    return all_entity_results_dicts


def _simulate_single_entity_consolidation(entity: EntityToScreen, checks: List[ScreeningCheckType]) -> Dict[str, Any]:
    """Helper function to mock the consolidation logic of the final CrewAI task for a single entity."""
    hits = []
    errors = []
    summary_parts = []
    overall_status: ScreeningStatus = "Clear" # type: ignore
    overall_risk: RiskRating = "Low" # type: ignore
    dob_str = entity.date_of_birth.isoformat() if entity.date_of_birth else None

    if "Sanctions" in checks:
        s_res = sanctions_list_tool.run({"entity_name": entity.name, "entity_type": entity.entity_type, "date_of_birth": dob_str, "nationality": entity.nationality})
        if s_res.get("status") == "Hit":
            hits.extend(s_res.get("hits",[]))
            overall_status = "ConfirmedHit" # type: ignore
            overall_risk = "Critical" # type: ignore
            summary_parts.append("Sanctions HIT.")
        elif s_res.get("status") == "Error": errors.append(f"Sanctions: {s_res.get('message')}")
        else: summary_parts.append("Sanctions: Clear.")

    if "PEP" in checks and entity.entity_type == "Individual" and overall_status != "ConfirmedHit": # type: ignore
        p_res = pep_screening_tool.run({"entity_name": entity.name, "date_of_birth": dob_str, "nationality": entity.nationality})
        if p_res.get("is_pep"):
            hits.append({"list_name": "PEP Database (Mock)", "matched_name": entity.name, "hit_reason": "Identified as PEP", "additional_match_info": p_res.get("pep_details")})
            if overall_status != "Error": overall_status = "PotentialHit" # type: ignore
            if overall_risk not in ["Critical", "High"]: overall_risk = "High" # type: ignore
            summary_parts.append("PEP: Identified.")
        elif p_res.get("error"): errors.append(f"PEP: {p_res.get('error')}")
        else: summary_parts.append("PEP: Clear.")

    if "AdverseMedia" in checks and overall_status != "ConfirmedHit": # type: ignore
        am_res = adverse_media_tool.run({"entity_name": entity.name})
        if am_res.get("media_hits_count", 0) > 0:
            hits.append({"list_name": "Adverse Media (Mock)", "matched_name": entity.name, "hit_reason": am_res.get('summary_of_findings'), "sample_urls": am_res.get('sample_hit_urls')})
            if overall_status != "Error": overall_status = "PotentialHit" # type: ignore
            if overall_risk not in ["Critical", "High"]: overall_risk = "Medium" # type: ignore
            summary_parts.append(f"Adverse Media: {am_res.get('summary_of_findings')}")
        elif am_res.get("error"): errors.append(f"Adverse Media: {am_res.get('error')}")
        else: summary_parts.append("Adverse Media: Clear.")

    if errors and overall_status != "ConfirmedHit": # type: ignore
        overall_status = "Error" # type: ignore
        overall_risk = "Medium" # type: ignore # Or Undetermined

    return {
        "entity_id": entity.entity_id, "input_name": entity.name,
        "screening_status": overall_status, "overall_risk_rating": overall_risk,
        "hits": hits if hits else None, "errors": errors if errors else None,
        "summary_message": " | ".join(summary_parts) or "Screening performed (mock consolidation).",
        "last_checked_at": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import asyncio

    async def test_compliance_screening_workflow_crew():
        print("--- Testing Compliance Agent Screening Workflow (Simulated CrewAI) ---")

        sample_entities_data = [
            {"entity_type": "Individual", "name": "Good Man Clem", "date_of_birth": "1990-05-05", "nationality": "NG"},
            {"entity_type": "Individual", "name": "Elena Petrova", "date_of_birth": "1975-03-10", "nationality": "RU", "aliases": ["Lena P."]},
            {"entity_type": "Organization", "name": "ACME Corp Overseas Ltd.", "country_of_incorporation": "BS"},
            {"entity_type": "Individual", "name": "Ngozi Okoro", "date_of_birth": "1965-11-20", "nationality": "NG"},
        ]
        entities_to_screen_models = [EntityToScreen(**data) for data in sample_entities_data]

        screening_req = ScreeningRequest(
            entities_to_screen=entities_to_screen_models,
            checks_to_perform=["Sanctions", "PEP", "AdverseMedia"]
        )

        print(f"\nTesting with Screening Request ID: {screening_req.request_id}")
        screening_results_list_dicts = await start_entity_screening_workflow_async(screening_req)

        print("\n--- Final Screening Results from Agent Workflow (Simulated CrewAI) ---")
        for i, result_dict in enumerate(screening_results_list_dicts):
            print(f"\nResult for Entity {i+1} ('{result_dict['input_name']}'):")
            print(json.dumps(result_dict, indent=2, default=str))
            try:
                ScreeningResult(**result_dict) # Validate against schema
                print(f"  (Schema validation successful for entity {result_dict['input_name']})")
            except Exception as e:
                print(f"  (SCHEMA VALIDATION FAILED for entity {result_dict['input_name']}: {e})")

    # To run tests:
    # logging.basicConfig(level=logging.DEBUG) # For more verbose logs
    # asyncio.run(test_compliance_screening_workflow_crew())
    print("Compliance Agent logic (agent.py) updated with CrewAI Agent and Task structure (simulated CrewAI kickoff).")
