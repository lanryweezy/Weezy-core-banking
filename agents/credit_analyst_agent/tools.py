# Conceptual tools for the Credit Analyst AI Agent
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Import relevant schemas from CBS modules
from weezy_cbs.loan_management_module import schemas as loan_schemas
from weezy_cbs.loan_management_module import services as loan_services
from weezy_cbs.loan_management_module.models import LoanApplicationStatusEnum # For status updates

from weezy_cbs.customer_identity_management import schemas as cim_schemas
from weezy_cbs.customer_identity_management import services as cim_services

from weezy_cbs.ai_automation_layer import schemas as ai_schemas
from weezy_cbs.ai_automation_layer import services as ai_services

# --- Tool Definitions ---

async def get_loan_application_details_tool(
    db: Session,
    application_id: int
) -> Optional[loan_schemas.LoanApplicationResponse]: # Assuming service returns this
    """Tool to fetch loan application details."""
    print(f"TOOL (CreditAnalyst): Fetching loan application ID: {application_id}")
    try:
        # The service method get_loan_application_by_id might need to be created or adjusted
        # to return the Pydantic schema or handle ORM object conversion.
        # For now, assuming it returns an ORM object that can be converted.
        app_orm = loan_services.loan_application_service.get_application_by_id(db, application_id) # Conceptual method name
        if app_orm:
            return loan_schemas.LoanApplicationResponse.from_orm(app_orm)
        return None
    except Exception as e: # Catch specific exceptions from service if defined
        print(f"TOOL_ERROR: Failed to fetch loan application {application_id}: {e}")
        return None


async def get_customer_details_tool(
    db: Session,
    customer_id: int
) -> Optional[cim_schemas.CustomerResponse]: # Assuming service returns this
    """Tool to fetch customer details."""
    print(f"TOOL (CreditAnalyst): Fetching customer details for ID: {customer_id}")
    try:
        customer_orm = cim_services.get_customer(db, customer_id=customer_id)
        if customer_orm:
            return cim_schemas.CustomerResponse.from_orm(customer_orm)
        return None
    except Exception as e:
        print(f"TOOL_ERROR: Failed to fetch customer {customer_id}: {e}")
        return None


async def calculate_credit_score_tool(
    db: Session,
    # customer_data: cim_schemas.CustomerResponse, # Or a subset of relevant features
    # loan_application_data: loan_schemas.LoanApplicationResponse # Or relevant features
    credit_score_request_data: ai_schemas.CreditScoreRequestData,
    triggering_user_id: Optional[int] = None # ID of the system user (agent/analyst) if applicable
) -> Optional[ai_schemas.CreditScoreResponseData]:
    """Tool to invoke the Credit Scoring AI service."""
    print(f"TOOL (CreditAnalyst): Calculating credit score for customer ID: {credit_score_request_data.customer_id}, app ID: {credit_score_request_data.loan_application_id}")
    try:
        # `credit_scoring_ai_service` is already instantiated in ai_automation_layer.services
        response = await ai_services.credit_scoring_ai_service.calculate_credit_score(
            db, request_data=credit_score_request_data, user_id_triggering=triggering_user_id
        )
        return response
    except Exception as e:
        print(f"TOOL_ERROR: Credit scoring failed: {e}")
        return None


async def evaluate_lending_rules_tool(
    db: Session,
    application_data: loan_schemas.LoanApplicationResponse, # Or a simpler dict
    customer_data: cim_schemas.CustomerResponse, # Or a simpler dict
    credit_score_data: ai_schemas.CreditScoreResponseData,
    rule_set_id: str # From agent config
) -> Dict[str, Any]:
    """
    Tool to evaluate lending rules using the AutomatedRule service (conceptual).
    Returns a mock evaluation result.
    """
    print(f"TOOL (CreditAnalyst): Evaluating lending rules (set: {rule_set_id}) for application ID: {application_data.id}")

    # Conceptual: Call ai_automation_layer.services.automated_rule_service.evaluate_rules(...)
    # This service would take context (app_data, customer_data, score_data) and rule_set_id,
    # then query AutomatedRule models and execute their logic.

    # Mock rule evaluation:
    approved = False
    reasons = []
    confidence = random.uniform(0.7, 0.95)

    if credit_score_data.score < 580:
        reasons.append("Credit score too low.")
    elif credit_score_data.score >= 650 and application_data.requested_amount <= 500000: # Simple mock rule
        approved = True
        reasons.append("Credit score and loan amount within acceptable parameters.")
    elif credit_score_data.score >= 600:
        reasons.append("Requires further review due to borderline score or other factors.")
        # Could set a 'manual_review_required' flag
    else:
        reasons.append("Application does not meet automated lending criteria.")

    return {
        "rule_set_evaluated": rule_set_id,
        "recommendation": "APPROVE" if approved else "REJECT" if reasons and not approved else "MANUAL_REVIEW",
        "reasons": reasons,
        "confidence": confidence,
        "evaluation_details": {"mock_rules_checked": ["SCORE_CHECK", "AMOUNT_CHECK"]}
    }


async def update_loan_application_status_tool(
    db: Session,
    application_id: int,
    new_status: str, # Should match LoanApplicationStatusEnum values
    decision_reason: Optional[str] = None,
    approved_amount: Optional[float] = None,
    approved_tenor: Optional[int] = None,
    credit_score: Optional[int] = None,
    risk_rating: Optional[str] = None,
    performing_user_id: str = "CreditAnalystAIAgent" # For audit log in service
) -> Optional[loan_schemas.LoanApplicationResponse]:
    """Tool to update the loan application status and decision details."""
    print(f"TOOL (CreditAnalyst): Updating loan application ID {application_id} to status {new_status}")
    try:
        # The service method needs to accept these fields.
        # We'll assume loan_services.loan_application_service.update_application_decision exists or is adapted.

        # Convert string status to Enum if service expects Enum
        try:
            status_enum = LoanApplicationStatusEnum[new_status.upper()]
        except KeyError:
            print(f"TOOL_ERROR: Invalid status string '{new_status}' for LoanApplicationStatusEnum.")
            return None

        update_schema = loan_schemas.LoanApplicationDecisionUpdate( # This schema might need to be created
            status=status_enum,
            decision_reason=decision_reason,
            approved_amount=approved_amount,
            approved_tenor_months=approved_tenor,
            credit_score=credit_score,
            risk_rating=risk_rating
        )

        # Conceptual call, assuming such a service method exists in loan_services.py
        # updated_app_orm = loan_services.loan_application_service.update_application_decision(
        #     db, application_id=application_id, decision_data=update_schema, updated_by_user_id=performing_user_id
        # )

        # Mocking the update:
        app_orm = loan_services.loan_application_service.get_application_by_id(db, application_id)
        if not app_orm: return None
        app_orm.status = status_enum
        app_orm.decision_reason = decision_reason
        if approved_amount is not None: app_orm.approved_amount = approved_amount
        if approved_tenor is not None: app_orm.approved_tenor_months = approved_tenor
        if credit_score is not None: app_orm.credit_score = credit_score
        if risk_rating is not None: app_orm.risk_rating = risk_rating
        if status_enum == LoanApplicationStatusEnum.APPROVED: app_orm.approved_at = datetime.utcnow()
        if status_enum == LoanApplicationStatusEnum.REJECTED: app_orm.rejected_at = datetime.utcnow()
        db.commit()
        db.refresh(app_orm)
        updated_app_orm = app_orm # End of mock

        if updated_app_orm:
            return loan_schemas.LoanApplicationResponse.from_orm(updated_app_orm)
        return None
    except Exception as e:
        print(f"TOOL_ERROR: Failed to update loan application {application_id}: {e}")
        return None
```
