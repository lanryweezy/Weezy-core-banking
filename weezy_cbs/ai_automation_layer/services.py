import json
from typing import List, Optional, Type, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import random # For mock results

from . import models, schemas
from weezy_cbs.core_infrastructure_config_engine.services import AuditLogService
# Conceptual: For making calls to external AI services if source_type is EXTERNAL_API_ENDPOINT
# from weezy_cbs.third_party_fintech_integration.services import GenericExternalAPICaller

# --- Base AI Service ---
class BaseAIService:
    def _audit_log(self, db: Session, action: str, entity_type: str, entity_id: Any, summary: str = "", performing_user: str = "SYSTEM"):
        AuditLogService.create_audit_log_entry(
            db, username_performing_action=performing_user, action_type=action,
            entity_type=entity_type, entity_id=str(entity_id), summary=summary
        )

    def _parse_json_field(self, data: Optional[str]) -> Optional[Any]:
        if data is None: return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON content in field", "original_data": data}

# --- AIModelMetadata Service ---
class AIModelMetadataService(BaseAIService):
    def create_model_metadata(self, db: Session, metadata_in: schemas.AIModelMetadataCreate, user_id: Optional[int], username: str) -> models.AIModelMetadata:
        if db.query(models.AIModelMetadata).filter(models.AIModelMetadata.model_name == metadata_in.model_name).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"AI Model with name '{metadata_in.model_name}' already exists.")

        db_metadata = models.AIModelMetadata(
            model_name=metadata_in.model_name,
            model_type=metadata_in.model_type,
            version=metadata_in.version,
            description=metadata_in.description,
            source_type=metadata_in.source_type,
            source_identifier=metadata_in.source_identifier,
            input_schema_json=json.dumps(metadata_in.input_schema_json) if metadata_in.input_schema_json else None,
            output_schema_json=json.dumps(metadata_in.output_schema_json) if metadata_in.output_schema_json else None,
            status=metadata_in.status,
            performance_metrics_json=json.dumps(metadata_in.performance_metrics_json) if metadata_in.performance_metrics_json else None,
            created_by_user_id=user_id,
            deployed_at=datetime.utcnow() if metadata_in.status == models.AIModelStatusEnum.ACTIVE else None
        )
        db.add(db_metadata)
        db.commit()
        db.refresh(db_metadata)
        self._audit_log(db, "AI_MODEL_METADATA_CREATE", "AIModelMetadata", db_metadata.id, f"AI Model '{db_metadata.model_name}' v{db_metadata.version} metadata created.", username)
        return db_metadata

    def get_model_metadata_by_id(self, db: Session, model_id: int) -> Optional[models.AIModelMetadata]:
        return db.query(models.AIModelMetadata).filter(models.AIModelMetadata.id == model_id).first()

    def get_model_metadata_by_name_version(self, db: Session, model_name: str, version: Optional[str] = None) -> Optional[models.AIModelMetadata]:
        query = db.query(models.AIModelMetadata).filter(models.AIModelMetadata.model_name == model_name)
        if version:
            query = query.filter(models.AIModelMetadata.version == version)
        else: # Get latest active version if no specific version
            query = query.filter(models.AIModelMetadata.status == models.AIModelStatusEnum.ACTIVE).order_by(models.AIModelMetadata.version.desc()) # Simplistic version sort
        return query.first()


    def get_all_model_metadata(self, db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[models.AIModelMetadata], int]:
        query = db.query(models.AIModelMetadata)
        total = query.count()
        metadata_list = query.order_by(models.AIModelMetadata.model_name, models.AIModelMetadata.version.desc()).offset(skip).limit(limit).all()
        return metadata_list, total

    def update_model_metadata(self, db: Session, model_id: int, metadata_upd: schemas.AIModelMetadataUpdate, username: str) -> Optional[models.AIModelMetadata]:
        db_metadata = self.get_model_metadata_by_id(db, model_id)
        if not db_metadata: return None

        update_data = metadata_upd.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field.endswith("_json") and isinstance(value, (dict,list)):
                    setattr(db_metadata, field, json.dumps(value))
                else:
                    setattr(db_metadata, field, value)

        if "status" in update_data and update_data["status"] == models.AIModelStatusEnum.ACTIVE and not db_metadata.deployed_at:
            db_metadata.deployed_at = datetime.utcnow()

        db_metadata.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_metadata)
        self._audit_log(db, "AI_MODEL_METADATA_UPDATE", "AIModelMetadata", db_metadata.id, f"AI Model '{db_metadata.model_name}' v{db_metadata.version} metadata updated.", username)
        return db_metadata

    def delete_model_metadata(self, db: Session, model_id: int, username: str) -> bool:
        db_metadata = self.get_model_metadata_by_id(db, model_id)
        if not db_metadata: return False
        # Check for dependencies (e.g., active AITaskLogs, AIAgentConfigs using this model) before deleting
        self._audit_log(db, "AI_MODEL_METADATA_DELETE", "AIModelMetadata", db_metadata.id, f"AI Model '{db_metadata.model_name}' v{db_metadata.version} metadata deleted.", username)
        db.delete(db_metadata)
        db.commit()
        return True

# --- AITaskLog Service ---
class AITaskLogService(BaseAIService):
    def create_task_log(self, db: Session, task_in: schemas.AITaskLogCreate) -> models.AITaskLog:
        db_log = models.AITaskLog(
            model_metadata_id=task_in.model_metadata_id,
            task_name=task_in.task_name,
            related_entity_type=task_in.related_entity_type,
            related_entity_id=task_in.related_entity_id,
            input_data_summary_json=json.dumps(task_in.input_data_summary_json) if task_in.input_data_summary_json else None,
            user_triggering_task_id=task_in.user_triggering_task_id,
            correlation_id=task_in.correlation_id,
            status=task_in.status, # Should be PENDING initially
            created_at=datetime.utcnow() # Explicitly set creation time
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log

    def update_task_log_start(self, db: Session, log_id: int) -> Optional[models.AITaskLog]:
        db_log = db.query(models.AITaskLog).filter(models.AITaskLog.id == log_id).first()
        if db_log and db_log.status == models.AITaskStatusEnum.PENDING:
            db_log.status = models.AITaskStatusEnum.PROCESSING
            db_log.started_at = datetime.utcnow()
            db.commit()
            db.refresh(db_log)
        return db_log

    def update_task_log_finish(
        self, db: Session, log_id: int, status: models.AITaskStatusEnum,
        output_summary: Optional[Dict] = None, confidence: Optional[float] = None,
        error_msg: Optional[str] = None
    ) -> Optional[models.AITaskLog]:
        db_log = db.query(models.AITaskLog).filter(models.AITaskLog.id == log_id).first()
        if not db_log: return None

        db_log.status = status
        db_log.output_data_summary_json = json.dumps(output_summary) if output_summary else None
        db_log.confidence_score = confidence
        db_log.error_message = error_msg
        db_log.completed_at = datetime.utcnow()
        if db_log.started_at:
            db_log.processing_duration_ms = int((db_log.completed_at - db_log.started_at).total_seconds() * 1000)

        db.commit()
        db.refresh(db_log)
        return db_log

    def get_task_log_by_id(self, db: Session, log_id: int) -> Optional[models.AITaskLog]:
        return db.query(models.AITaskLog).options(joinedload(models.AITaskLog.model_metadata)).filter(models.AITaskLog.id == log_id).first()

    def get_task_logs( self, db: Session, model_id: Optional[int] = None, task_name: Optional[str] = None,
                       status: Optional[models.AITaskStatusEnum] = None, related_entity_type: Optional[str] = None,
                       related_entity_id: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> Tuple[List[models.AITaskLog], int]:
        query = db.query(models.AITaskLog).options(joinedload(models.AITaskLog.model_metadata))
        if model_id: query = query.filter(models.AITaskLog.model_metadata_id == model_id)
        if task_name: query = query.filter(models.AITaskLog.task_name.ilike(f"%{task_name}%"))
        if status: query = query.filter(models.AITaskLog.status == status)
        if related_entity_type: query = query.filter(models.AITaskLog.related_entity_type == related_entity_type)
        if related_entity_id: query = query.filter(models.AITaskLog.related_entity_id == related_entity_id)

        total = query.count()
        logs = query.order_by(models.AITaskLog.created_at.desc()).offset(skip).limit(limit).all()
        return logs, total

# --- AIAgentConfig Service ---
class AIAgentConfigService(BaseAIService):
    # CRUD for AIAgentConfig
    def create_agent_config(self, db: Session, agent_in: schemas.AIAgentConfigCreate, user_id: Optional[int], username: str) -> models.AIAgentConfig:
        if db.query(models.AIAgentConfig).filter(models.AIAgentConfig.agent_name == agent_in.agent_name).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"AI Agent with name '{agent_in.agent_name}' already exists.")

        db_agent_cfg = models.AIAgentConfig(
            agent_name=agent_in.agent_name,
            role_description=agent_in.role_description,
            goal_description=agent_in.goal_description,
            backstory=agent_in.backstory,
            llm_config_json=json.dumps(agent_in.llm_config_json.dict()) if agent_in.llm_config_json else None,
            tools_config_json=json.dumps([t.dict() for t in agent_in.tools_config_json]) if agent_in.tools_config_json else None,
            is_active=agent_in.is_active,
            version=agent_in.version,
            created_by_user_id=user_id
        )
        db.add(db_agent_cfg)
        db.commit()
        db.refresh(db_agent_cfg)
        self._audit_log(db, "AI_AGENT_CONFIG_CREATE", "AIAgentConfig", db_agent_cfg.id, f"AI Agent Config '{db_agent_cfg.agent_name}' created.", username)
        return db_agent_cfg

    # ... other CRUD methods for AIAgentConfig (get_by_id, get_all, update, delete) ...

# --- AutomatedRule Service ---
class AutomatedRuleService(BaseAIService):
    # CRUD for AutomatedRule
    # Conceptual: evaluate_rule(db, rule_id, context_data) -> bool or actions
    pass


# --- Conceptual AI Model Invocation Services ---
# These services simulate calling AI models and log tasks.
# They do not contain actual ML/AI code but define the interface.

class BaseAIModelInvocationService(BaseAIService):
    def __init__(self, task_log_service: AITaskLogService, model_meta_service: AIModelMetadataService):
        self.task_log_service = task_log_service
        self.model_meta_service = model_meta_service

    async def _invoke_model_and_log(
        self, db: Session, model_name: str, model_version: Optional[str], task_name: str,
        request_data_schema: BaseModel, # Pydantic schema of input
        response_schema_type: Type[BaseModel], # Pydantic schema type for mock output
        mock_result_generator: callable, # Function to generate mock result
        related_entity_type: Optional[str] = None, related_entity_id: Optional[str] = None,
        correlation_id: Optional[str] = None, user_id_triggering: Optional[int] = None
    ) -> Any: # Returns instance of response_schema_type or raises error

        model_meta = self.model_meta_service.get_model_metadata_by_name_version(db, model_name, model_version)
        if not model_meta or model_meta.status != models.AIModelStatusEnum.ACTIVE:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI Model '{model_name}' (version: {version or 'latest active'}) not available.")

        task_log_create = schemas.AITaskLogCreate(
            model_metadata_id=model_meta.id,
            task_name=task_name,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            input_data_summary_json=request_data_schema.dict(), # Full input for mock, summarize in real app
            user_triggering_task_id=user_id_triggering,
            correlation_id=correlation_id,
            status=models.AITaskStatusEnum.PENDING
        )
        task_log = self.task_log_service.create_task_log(db, task_log_create)
        self.task_log_service.update_task_log_start(db, task_log.id)

        try:
            # Simulate model invocation based on source_type
            # if model_meta.source_type == "EXTERNAL_API_ENDPOINT":
            #    # Use GenericExternalAPICaller from third_party_integration module
            #    # api_caller = GenericExternalAPICaller(...)
            #    # response_data = await api_caller.make_request(...)
            #    # mock_output = response_schema_type.parse_obj(response_data_json)
            #    pass
            # else: # Simulate internal model call
            await asyncio.sleep(random.uniform(0.1, 0.5)) # Simulate processing time (requires asyncio)

            mock_output_data = mock_result_generator(request_data_schema)
            mock_output = response_schema_type.parse_obj(mock_output_data)

            self.task_log_service.update_task_log_finish(
                db, task_log.id, models.AITaskStatusEnum.SUCCESS,
                output_summary=mock_output.dict(), # Full output for mock
                confidence=getattr(mock_output, 'confidence', None) or getattr(mock_output, 'fraud_score', None) # Example
            )
            return mock_output
        except Exception as e:
            self.task_log_service.update_task_log_finish(db, task_log.id, models.AITaskStatusEnum.FAILED, error_msg=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during AI task '{task_name}': {str(e)}")


class CreditScoringAIService(BaseAIModelInvocationService):
    MODEL_NAME = "NIGERIAN_CREDIT_SCORER" # Corresponds to AIModelMetadata.model_name

    def _generate_mock_score(self, req: schemas.CreditScoreRequestData) -> Dict:
        score = random.randint(300, 850)
        risk = "LOW"
        if score < 500: risk = "HIGH"
        elif score < 650: risk = "MEDIUM"
        return {
            "request_reference_id": str(req.loan_application_id or req.customer_id),
            "score": score, "risk_level": risk, "model_name_used": self.MODEL_NAME, "model_version_used": "1.1-mock"
        }

    async def calculate_credit_score(self, db: Session, request_data: schemas.CreditScoreRequestData, user_id_triggering: Optional[int] = None) -> schemas.CreditScoreResponseData:
        return await self._invoke_model_and_log(
            db, model_name=self.MODEL_NAME, model_version=None, task_name="CREDIT_SCORE_CALCULATION",
            request_data_schema=request_data, response_schema_type=schemas.CreditScoreResponseData,
            mock_result_generator=self._generate_mock_score,
            related_entity_type="LoanApplication", related_entity_id=str(request_data.loan_application_id) if request_data.loan_application_id else str(request_data.customer_id),
            user_id_triggering=user_id_triggering
        )

class FraudDetectionAIService(BaseAIModelInvocationService):
    MODEL_NAME = "TRANSACTION_FRAUD_DETECTOR"

    def _generate_mock_fraud_check(self, req: schemas.FraudDetectionRequestData) -> Dict:
        is_fraud = random.choice([True, False, False]) # Skew towards not fraud
        score = random.uniform(0.01, 0.99) if is_fraud else random.uniform(0.01, 0.4)
        return {
            "request_reference_id": req.transaction_id, "is_fraud_suspected": is_fraud, "fraud_score": score,
            "model_name_used": self.MODEL_NAME, "model_version_used": "2.0-mock"
        }

    async def check_transaction_for_fraud(self, db: Session, request_data: schemas.FraudDetectionRequestData, user_id_triggering: Optional[int] = None) -> schemas.FraudDetectionResponseData:
        return await self._invoke_model_and_log(
            db, model_name=self.MODEL_NAME, model_version=None, task_name="TRANSACTION_FRAUD_CHECK",
            request_data_schema=request_data, response_schema_type=schemas.FraudDetectionResponseData,
            mock_result_generator=self._generate_mock_fraud_check,
            related_entity_type="FinancialTransaction", related_entity_id=request_data.transaction_id,
            user_id_triggering=user_id_triggering
        )

# ... Other conceptual services like LLMService, DocumentParsingService, FaceMatchService ...

# --- AIAgentExecutionService (Conceptual) ---
class AIAgentExecutionService(BaseAIService):
    # This would orchestrate agents defined in AIAgentConfig, using their LLM and tools.
    # Highly conceptual for now.
    pass


# Instantiate services
ai_model_metadata_service = AIModelMetadataService()
ai_task_log_service = AITaskLogService()
ai_agent_config_service = AIAgentConfigService() # Add CRUD methods to this service
automated_rule_service = AutomatedRuleService() # Add CRUD methods to this service

# Invocation services (need task_log_service and model_meta_service)
# These might be better instantiated where db session is available, or have services passed.
# For now, global instantiation for structure, but be mindful of session management.
credit_scoring_ai_service = CreditScoringAIService(ai_task_log_service, ai_model_metadata_service)
fraud_detection_ai_service = FraudDetectionAIService(ai_task_log_service, ai_model_metadata_service)

# Import asyncio if not already imported at the top
import asyncio
