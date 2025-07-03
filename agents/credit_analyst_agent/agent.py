# Main logic for the Credit Analyst AI Agent
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json # For logging complex data

# Agent specific config and tools
from . import config as agent_config
from . import tools as agent_tools

# CBS Schemas
from weezy_cbs.loan_management_module import schemas as loan_schemas
from weezy_cbs.loan_management_module.models import LoanApplicationStatusEnum # For status updates
from weezy_cbs.customer_identity_management import schemas as cim_schemas
from weezy_cbs.ai_automation_layer import schemas as ai_schemas
# CBS Services (especially for logging AI tasks)
from weezy_cbs.ai_automation_layer import services as ai_services
from weezy_cbs.ai_automation_layer import models as ai_models # For AITaskStatusEnum

class CreditAnalystAIAgent:
    def __init__(self, db: Session):
        self.db = db
        self.agent_name = agent_config.AGENT_CONFIG_NAME
        self.ai_task_logger = ai_services.ai_task_log_service

    def _log_agent_task_start(self, application_id: int) -> models.AITaskLog:
        log_create_schema = ai_schemas.AITaskLogCreate(
            task_name=f"{self.agent_name}_LoanAssessment",
            related_entity_type="LoanApplication",
            related_entity_id=str(application_id),
            input_data_summary_json={"application_id": application_id},
            status=ai_models.AITaskStatusEnum.PROCESSING
        )
        log_entry = self.ai_task_logger.create_task_log(self.db, log_create_schema)
        return log_entry

    def _log_agent_task_finish(self, log_entry: models.AITaskLog, status: ai_models.AITaskStatusEnum, output_summary: Dict, error_msg: Optional[str] = None):
        self.ai_task_logger.update_task_log_finish(
            self.db, log_entry.id, status,
            output_summary=output_summary,
            error_msg=error_msg
        )

    async def assess_loan_application(self, application_id: int) -> Dict[str, Any]:
        """
        Orchestrates the loan application assessment process.
        1. Fetches application and customer data.
        2. Calculates credit score.
        3. Evaluates lending rules.
        4. Makes a recommendation/decision.
        5. Updates application status.
        6. Logs the process.
        Returns a summary of the assessment.
        """
        main_task_log = self._log_agent_task_start(application_id)

        assessment_outcome = {
            "application_id": application_id,
            "decision": "ERROR", # Default
            "reason": "Assessment could not be completed.",
            "details": {}
        }

        try:
            # --- Step 1: Fetch Loan Application Details ---
            loan_app_data = await agent_tools.get_loan_application_details_tool(self.db, application_id)
            if not loan_app_data:
                raise Exception(f"Loan application ID {application_id} not found.")
            assessment_outcome["details"]["loan_application"] = loan_app_data.dict()

            # --- Step 2: Fetch Customer Details ---
            customer_data = await agent_tools.get_customer_details_tool(self.db, loan_app_data.customer_id)
            if not customer_data:
                raise Exception(f"Customer ID {loan_app_data.customer_id} for application {application_id} not found.")
            assessment_outcome["details"]["customer_data"] = customer_data.dict()

            # --- Step 3: Calculate Credit Score ---
            # Prepare data for credit scoring service
            # This would involve feature engineering in a real scenario.
            # For mock, we pass IDs. The mock service generates a score.
            credit_score_req_data = ai_schemas.CreditScoreRequestData(
                customer_id=customer_data.id,
                loan_application_id=loan_app_data.id
                # Populate with more features from customer_data and loan_app_data as needed by the actual model
            )
            credit_score_response = await agent_tools.calculate_credit_score_tool(
                self.db, credit_score_request_data=credit_score_req_data,
                triggering_user_id=None # System task
            )
            if not credit_score_response:
                raise Exception("Credit scoring service failed or returned no response.")
            assessment_outcome["details"]["credit_score_info"] = credit_score_response.dict()

            # --- Step 4: Evaluate Lending Rules ---
            rule_eval_result = await agent_tools.evaluate_lending_rules_tool(
                self.db,
                application_data=loan_app_data, # Pass the Pydantic model
                customer_data=customer_data,     # Pass the Pydantic model
                credit_score_data=credit_score_response,
                rule_set_id=agent_config.LENDING_RULE_SET_ID
            )
            assessment_outcome["details"]["rule_evaluation"] = rule_eval_result

            # --- Step 5: Make Decision (Simplified Logic) ---
            final_decision = rule_eval_result.get("recommendation", "MANUAL_REVIEW")
            decision_reason = ", ".join(rule_eval_result.get("reasons", ["Automated assessment completed."]))

            # Override based on hard thresholds from config if needed
            if credit_score_response.score < agent_config.MIN_CREDIT_SCORE_THRESHOLD_AUTO and final_decision == "APPROVE":
                final_decision = "MANUAL_REVIEW" # Or REJECT
                decision_reason = f"Score {credit_score_response.score} below auto-approval threshold. " + decision_reason

            if agent_config.CREDIT_SCORE_MANUAL_REVIEW_RANGE_MIN <= credit_score_response.score <= agent_config.CREDIT_SCORE_MANUAL_REVIEW_RANGE_MAX:
                if final_decision == "APPROVE": # If rules approved but score is in manual review range
                     final_decision = "MANUAL_REVIEW"
                     decision_reason = f"Score {credit_score_response.score} falls into manual review range. " + decision_reason


            assessment_outcome["decision"] = final_decision
            assessment_outcome["reason"] = decision_reason

            # --- Step 6: Update Application Status (if configured) ---
            new_loan_app_status_str = "UNDER_REVIEW" # Default if needs manual review
            if final_decision == "APPROVE":
                new_loan_app_status_str = LoanApplicationStatusEnum.APPROVED.value
            elif final_decision == "REJECT":
                new_loan_app_status_str = LoanApplicationStatusEnum.REJECTED.value
            # MANUAL_REVIEW maps to UNDER_REVIEW or a specific PENDING_ANALYST_REVIEW status

            if agent_config.AUTO_UPDATE_APPLICATION_STATUS:
                print(f"AGENT: Auto-updating application {application_id} to status {new_loan_app_status_str}")
                updated_app = await agent_tools.update_loan_application_status_tool(
                    self.db,
                    application_id=application_id,
                    new_status=new_loan_app_status_str,
                    decision_reason=decision_reason,
                    approved_amount=loan_app_data.requested_amount if final_decision == "APPROVE" else None, # Mock: approve requested amount
                    approved_tenor=loan_app_data.requested_tenor_months if final_decision == "APPROVE" else None,
                    credit_score=credit_score_response.score,
                    risk_rating=credit_score_response.risk_level,
                    performing_user_id=self.agent_name
                )
                if not updated_app:
                    assessment_outcome["reason"] += " | Failed to update application status via tool."
                    # Don't override main decision, just note update failure.
                else:
                    assessment_outcome["details"]["updated_application_status"] = updated_app.status.value

            self._log_agent_task_finish(main_task_log, ai_models.AITaskStatusEnum.SUCCESS, assessment_outcome)

        except Exception as e:
            print(f"AGENT_ERROR: Exception in assess_loan_application for ID {application_id}: {e}")
            assessment_outcome["decision"] = "ERROR"
            assessment_outcome["reason"] = f"System error during assessment: {str(e)}"
            self._log_agent_task_finish(main_task_log, ai_models.AITaskStatusEnum.FAILED, assessment_outcome, error_msg=str(e))

        return assessment_outcome


if __name__ == '__main__':
    # Conceptual test of Credit Analyst Agent
    import asyncio

    class MockDBSession: # Same mock as before
        def add(self, obj): print(f"MockDB: Add {obj}")
        def commit(self): print("MockDB: Commit")
        def refresh(self, obj): print(f"MockDB: Refresh {obj}")
        def query(self, *args):
            class MockQuery:
                def filter(self, *criterion): return self
                def first(self):
                    # Simulate finding loan app and customer for a specific ID
                    # This needs to be smarter for testing different scenarios
                    if hasattr(criterion[0].left, 'name') and criterion[0].left.name == 'id':
                        entity_id = criterion[0].right.value
                        if entity_id == 1: # Assume app_id 1
                            # Return mock LoanApplication ORM object
                            mock_app = models.LoanApplication(id=1, customer_id=101, loan_product_id=1, requested_amount=200000, requested_tenor_months=12, status=LoanApplicationStatusEnum.SUBMITTED)
                            # mock_app.customer = models.Customer(id=101, first_name="Test", last_name="Borrower", email="borrower@test.com") # This won't work directly, relationships are complex
                            return mock_app
                        if entity_id == 101: # Assume customer_id 101
                             # Return mock Customer ORM object
                            return models.Customer(id=101, first_name="Test", last_name="Borrower", email="borrower@test.com", phone_number="08012345678")
                    return None
                def count(self): return 0
                def all(self): return []
                def options(self, *args): return self
                def offset(self, val): return self
                def limit(self, val): return self
                def order_by(self, val): return self
            return MockQuery()

    mock_db = MockDBSession()

    # Mock necessary services if tools call them directly and they expect ORM objects
    # For this test, tools.py methods are designed to return Pydantic schemas or handle ORM internally
    # so we only need to ensure the mock_db.query().first() returns something that from_orm can use.
    # The ORM objects need to be instances of the actual SQLAlchemy models.

    async def main_test():
        print("--- Conceptual Test of Credit Analyst Agent ---")
        agent = CreditAnalystAIAgent(db=mock_db) # type: ignore

        # Test with a mock application ID that should exist in MockDBSession logic
        application_id_to_test = 1

        result = await agent.assess_loan_application(application_id_to_test)

        print("\n--- Assessment Result ---")
        print(json.dumps(result, indent=2, default=str))

    asyncio.run(main_test())
```
