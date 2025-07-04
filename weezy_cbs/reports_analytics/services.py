import json
from typing import List, Optional, Type, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text # For executing raw SQL safely
from fastapi import HTTPException, status
from datetime import datetime, timedelta
# import pandas as pd # Optional: For data manipulation and CSV/Excel export if used
import csv # For CSV generation
import io # For CSV generation

from . import models, schemas
from weezy_cbs.core_infrastructure_config_engine.services import AuditLogService
# Conceptual: For mapping model names to actual SQLAlchemy models for dynamic queries
# from weezy_cbs import models as all_models # This would require a central models.__init__

# --- Helper for Cron & Next Run Time (Conceptual) ---
# In a real app, use a library like 'croniter'
def calculate_next_run(cron_expression: str, last_run: Optional[datetime] = None) -> Optional[datetime]:
    # This is a placeholder. Real implementation needs a cron expression parser.
    # For simplicity, let's assume it just adds a fixed interval for demo.
    if "0 0 * * *" in cron_expression: # Daily at midnight
        return (last_run or datetime.utcnow()).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    if "0 * * * *" in cron_expression: # Hourly
        return (last_run or datetime.utcnow()).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    # Add more cron patterns or use a library
    return datetime.utcnow() + timedelta(days=1) # Default to next day for unknown


# --- Base Reporting Service ---
class BaseReportingService:
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
            # Log error or handle as appropriate
            return None # Or raise ValueError

# --- ReportDefinition Service ---
class ReportDefinitionService(BaseReportingService):
    def create_definition(self, db: Session, def_in: schemas.ReportDefinitionCreate, user_id: int, username: str) -> models.ReportDefinition:
        if db.query(models.ReportDefinition).filter(models.ReportDefinition.report_code == def_in.report_code).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Report code '{def_in.report_code}' already exists.")

        db_def = models.ReportDefinition(
            report_code=def_in.report_code,
            report_name=def_in.report_name,
            description=def_in.description,
            source_modules_json=json.dumps(def_in.source_modules_json) if def_in.source_modules_json else None,
            query_logic_type=def_in.query_logic_type,
            query_details_json=json.dumps(def_in.query_details_json.dict() if hasattr(def_in.query_details_json, 'dict') else def_in.query_details_json),
            parameters_schema_json=json.dumps(def_in.parameters_schema_json.dict()) if def_in.parameters_schema_json else None,
            default_output_formats_json=json.dumps(def_in.default_output_formats_json) if def_in.default_output_formats_json else None,
            allowed_roles_json=json.dumps(def_in.allowed_roles_json) if def_in.allowed_roles_json else None,
            is_system_report=def_in.is_system_report,
            version=def_in.version,
            created_by_user_id=user_id
        )
        db.add(db_def)
        db.commit()
        db.refresh(db_def)
        self._audit_log(db, "REPORT_DEF_CREATE", "ReportDefinition", db_def.id, f"Report definition '{db_def.report_name}' created.", username)
        return db_def

    def get_definition_by_id(self, db: Session, def_id: int) -> Optional[models.ReportDefinition]:
        return db.query(models.ReportDefinition).filter(models.ReportDefinition.id == def_id).first()

    def get_definition_by_code(self, db: Session, report_code: str) -> Optional[models.ReportDefinition]:
        return db.query(models.ReportDefinition).filter(models.ReportDefinition.report_code == report_code).order_by(models.ReportDefinition.version.desc()).first()


    def get_definitions(self, db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[models.ReportDefinition], int]:
        query = db.query(models.ReportDefinition)
        total = query.count()
        defs = query.order_by(models.ReportDefinition.report_name).offset(skip).limit(limit).all()
        return defs, total

    def update_definition(self, db: Session, def_id: int, def_upd: schemas.ReportDefinitionUpdate, username: str) -> Optional[models.ReportDefinition]:
        db_def = self.get_definition_by_id(db, def_id)
        if not db_def: return None

        update_data = def_upd.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None: # Ensure optional fields are not set to None if not provided
                # Handle JSON fields specifically
                if field.endswith("_json") and value is not None:
                    setattr(db_def, field, json.dumps(value.dict() if hasattr(value, 'dict') else value))
                else:
                    setattr(db_def, field, value)

        db_def.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_def)
        self._audit_log(db, "REPORT_DEF_UPDATE", "ReportDefinition", db_def.id, f"Report definition '{db_def.report_name}' updated.", username)
        return db_def

    def delete_definition(self, db: Session, def_id: int, username: str) -> bool:
        db_def = self.get_definition_by_id(db, def_id)
        if not db_def: return False
        # Consider implications: what happens to scheduled reports using this def? (ondelete=CASCADE handles DB level)
        self._audit_log(db, "REPORT_DEF_DELETE", "ReportDefinition", db_def.id, f"Report definition '{db_def.report_name}' deleted.", username)
        db.delete(db_def)
        db.commit()
        return True

# --- GeneratedReportLog Service ---
class GeneratedReportLogService(BaseReportingService):
    def create_log_entry(self, db: Session, report_name: str, generated_by_user_id: int, output_format: str,
                         report_def_id: Optional[int] = None, scheduled_rep_id: Optional[int] = None,
                         params_used: Optional[Dict[str, Any]] = None) -> models.GeneratedReportLog:
        db_log = models.GeneratedReportLog(
            report_definition_id=report_def_id,
            scheduled_report_id=scheduled_rep_id,
            report_name_generated=report_name,
            generated_by_user_id=generated_by_user_id,
            parameters_used_json=json.dumps(params_used) if params_used else None,
            output_format=output_format,
            status=models.ReportStatusEnum.PENDING
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log

    def update_log_status_success(self, db: Session, log_id: int, file_name: Optional[str], file_path: Optional[str], file_size: Optional[int], processing_time_sec: Optional[int]):
        db_log = db.query(models.GeneratedReportLog).filter(models.GeneratedReportLog.id == log_id).first()
        if db_log:
            db_log.status = models.ReportStatusEnum.SUCCESS
            db_log.file_name = file_name
            db_log.file_path_or_link = file_path
            db_log.file_size_bytes = file_size
            db_log.processing_time_seconds = processing_time_sec
            db_log.error_message = None
            db.commit()
            db.refresh(db_log)
        return db_log

    def update_log_status_failed(self, db: Session, log_id: int, error_message: str, processing_time_sec: Optional[int]):
        db_log = db.query(models.GeneratedReportLog).filter(models.GeneratedReportLog.id == log_id).first()
        if db_log:
            db_log.status = models.ReportStatusEnum.FAILED
            db_log.error_message = error_message
            db_log.processing_time_seconds = processing_time_sec
            db.commit()
            db.refresh(db_log)
        return db_log

    def get_log_by_id(self, db: Session, log_id: int) -> Optional[models.GeneratedReportLog]:
        return db.query(models.GeneratedReportLog).options(joinedload(models.GeneratedReportLog.report_definition)).filter(models.GeneratedReportLog.id == log_id).first()

    def get_logs(self, db: Session, user_id: Optional[int] = None, definition_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> Tuple[List[models.GeneratedReportLog], int]:
        query = db.query(models.GeneratedReportLog).options(joinedload(models.GeneratedReportLog.report_definition))
        if user_id: query = query.filter(models.GeneratedReportLog.generated_by_user_id == user_id)
        if definition_id: query = query.filter(models.GeneratedReportLog.report_definition_id == definition_id)
        total = query.count()
        logs = query.order_by(models.GeneratedReportLog.generation_timestamp.desc()).offset(skip).limit(limit).all()
        return logs, total

# --- ReportGeneration Service (Core Logic) ---
class ReportGenerationService(BaseReportingService):
    def __init__(self, db: Session, log_service: GeneratedReportLogService, def_service: ReportDefinitionService):
        self.db = db # Pass session for complex queries
        self.log_service = log_service
        self.def_service = def_service

    def _format_data_to_csv(self, data: List[Dict[str, Any]]) -> str:
        if not data: return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def _execute_sql_report(self, sql_template: str, params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # IMPORTANT: Ensure params are safely bound, not directly formatted into SQL string, to prevent SQL injection.
        # SQLAlchemy's text() handles parameter binding.
        stmt = text(sql_template)
        result_proxy = self.db.execute(stmt, params or {})
        # Convert rows to list of dicts
        # data = [dict(row) for row in result_proxy] # For SQLAlchemy 1.x
        data = [dict(row._mapping) for row in result_proxy] # For SQLAlchemy 2.x with Row._mapping
        return data

    def _execute_dynamic_filter_report(self, model_name: str, filters: Dict, select_fields: Optional[List[str]], sort_by: Optional[str]) -> List[Dict[str, Any]]:
        # This is highly conceptual and complex.
        # It requires a mapping from model_name (string) to actual SQLAlchemy model classes.
        # And a robust filter parser to convert {"field": "op:value"} into SQLAlchemy filter conditions.
        # This is highly conceptual and complex.
        # It requires a mapping from model_name (string) to actual SQLAlchemy model classes.
        # And a robust filter parser to convert {"field": "op:value"} into SQLAlchemy filter conditions.

        # Conceptual model map - in a real system, this would be more robust, possibly auto-discovered
        # or explicitly registered. For now, using placeholder models from other modules.
        # This assumes models from other modules are importable.
        from weezy_cbs.customer_identity_management.models import Customer
        from weezy_cbs.accounts_ledger_management.models import Account, LedgerEntry
        from weezy_cbs.transaction_management.models import FinancialTransaction

        MODEL_MAP = {
            "Customer": Customer,
            "Account": Account,
            "LedgerEntry": LedgerEntry,
            "FinancialTransaction": FinancialTransaction,
            # ... add other queryable models ...
        }

        target_model = MODEL_MAP.get(model_name)
        if not target_model:
            raise ValueError(f"Unsupported model for dynamic filtering: {model_name}")

        query = self.db.query(target_model)

        # Apply filters (conceptual parsing)
        # Filters format: {"field_name": "operator:value", "age": "gte:30", "status": "in:ACTIVE,PENDING"}
        if filters:
            for field_key, filter_value_str in filters.items():
                parts = filter_value_str.split(":", 1)
                operator = parts[0].lower()
                value_str = parts[1] if len(parts) > 1 else ""

                column_attr = getattr(target_model, field_key, None)
                if not column_attr:
                    print(f"WARN: Invalid filter field '{field_key}' for model '{model_name}'. Skipping.")
                    continue

                # Convert value based on column type (simplified - real type conversion needed)
                actual_value: Any = value_str
                # TODO: Add type conversion based on column_attr.type (e.g., for int, date, bool)
                # For 'in' operator, split by comma
                if operator == "in_" or operator == "notin_":
                    actual_value = [v.strip() for v in value_str.split(',')]
                elif isinstance(column_attr.type, (sqlalchemy.Integer, sqlalchemy.Numeric)):
                    try: actual_value = int(value_str) if isinstance(column_attr.type, sqlalchemy.Integer) else float(value_str)
                    except ValueError: print(f"WARN: Could not convert value '{value_str}' for field '{field_key}'. Skipping filter."); continue
                elif isinstance(column_attr.type, sqlalchemy.Date):
                    try: actual_value = datetime.strptime(value_str, '%Y-%m-%d').date()
                    except ValueError: print(f"WARN: Could not convert date value '{value_str}' for field '{field_key}'. Use YYYY-MM-DD. Skipping filter."); continue
                elif isinstance(column_attr.type, sqlalchemy.Boolean):
                    actual_value = value_str.lower() in ['true', '1', 'yes']


                if operator == "eq": query = query.filter(column_attr == actual_value)
                elif operator == "ne": query = query.filter(column_attr != actual_value)
                elif operator == "gt": query = query.filter(column_attr > actual_value)
                elif operator == "gte": query = query.filter(column_attr >= actual_value)
                elif operator == "lt": query = query.filter(column_attr < actual_value)
                elif operator == "lte": query = query.filter(column_attr <= actual_value)
                elif operator == "like": query = query.filter(column_attr.like(f"%{actual_value}%"))
                elif operator == "ilike": query = query.filter(column_attr.ilike(f"%{actual_value}%"))
                elif operator == "in_": query = query.filter(column_attr.in_(actual_value))
                elif operator == "notin_": query = query.filter(column_attr.notin_(actual_value))
                else: print(f"WARN: Unsupported operator '{operator}' for field '{field_key}'. Skipping filter.")


        # Apply select_fields
        if select_fields:
            selected_columns = [getattr(target_model, field) for field in select_fields if hasattr(target_model, field)]
            if selected_columns:
                query = query.with_entities(*selected_columns)

        # Apply sort_by (e.g., "field_name:asc" or "field_name:desc")
        if sort_by:
            sort_field_name, direction = (sort_by.split(":") + ["asc"])[:2] # Default to asc
            sort_column = getattr(target_model, sort_field_name, None)
            if sort_column:
                query = query.order_by(sort_column.desc() if direction.lower() == "desc" else sort_column.asc())

        results_orm = query.all()

        # Convert results to list of dicts
        data = []
        if results_orm:
            if select_fields and selected_columns: # If specific columns were selected
                 data = [dict(zip(select_fields, row)) for row in results_orm]
            else: # Full model objects
                 data = [ {c.name: getattr(row, c.name) for c in target_model.__table__.columns} for row in results_orm]

        print(f"SIMULATED DYNAMIC FILTER RESULT for {model_name}: Found {len(data)} records.")
        return data


    def generate_report_from_definition(self, def_id: int, params: Optional[Dict[str, Any]], output_format: str, generated_by_user_id: int, username: str) -> models.GeneratedReportLog:
        report_def = self.def_service.get_definition_by_id(self.db, def_id)
        if not report_def:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report definition not found.")

        log_entry = self.log_service.create_log_entry(
            self.db, report_name=report_def.report_name, generated_by_user_id=generated_by_user_id,
            output_format=output_format, report_def_id=report_def.id, params_used=params
        )

        start_time = datetime.utcnow()
        raw_data: List[Dict[str, Any]] = []
        error_msg: Optional[str] = None

        try:
            # Validate params against report_def.parameters_schema_json (conceptual)
            # ...

            query_details = self._parse_json_field(report_def.query_details_json)
            if not query_details:
                raise ValueError("Invalid query details in report definition.")

            if report_def.query_logic_type == models.ReportQueryLogicTypeEnum.PREDEFINED_SQL:
                if not isinstance(query_details, dict) or "sql_template" not in query_details:
                     raise ValueError("SQL template missing in query details for PREDEFINED_SQL report.")
                raw_data = self._execute_sql_report(query_details["sql_template"], params)

            elif report_def.query_logic_type == models.ReportQueryLogicTypeEnum.DYNAMIC_FILTERS_ON_MODEL:
                # This requires query_details to be parsed into schemas.QueryDetailsDynamicFilters
                # For simplicity, assuming it's already a dict with expected keys.
                if not isinstance(query_details, dict) or "base_model_name" not in query_details:
                    raise ValueError("Base model name missing for DYNAMIC_FILTERS report.")
                raw_data = self._execute_dynamic_filter_report(
                    query_details["base_model_name"],
                    params or {}, # Assuming params directly map to filters for this type
                    query_details.get("default_select_fields"),
                    query_details.get("default_sort_by")
                )
            elif report_def.query_logic_type == models.ReportQueryLogicTypeEnum.PYTHON_SCRIPT:
                # Placeholder: Invoke a python script/function
                # raw_data = some_python_script_runner(query_details.get("script_path"), params)
                raise NotImplementedError("Python script execution for reports not yet implemented.")
            else:
                raise ValueError(f"Unsupported query logic type: {report_def.query_logic_type}")

            # Format data (conceptual - only CSV implemented simply)
            formatted_output: Union[str, List[Dict[str, Any]]]
            file_name_final = f"{report_def.report_code.replace(' ','_')}_{start_time.strftime('%Y%m%d%H%M%S')}.{output_format.lower()}"

            if output_format.upper() == "CSV":
                formatted_output = self._format_data_to_csv(raw_data)
                # In real app, save to S3/file system and get path/link
                # For now, we'll just indicate success and conceptually store it.
                file_path_final = f"/reports_storage/{file_name_final}" # Placeholder
                file_size_final = len(formatted_output.encode('utf-8'))

                self.log_service.update_log_status_success(
                    self.db, log_entry.id, file_name_final, file_path_final, file_size_final,
                    int((datetime.utcnow() - start_time).total_seconds())
                )
            elif output_format.upper() == "JSON":
                formatted_output = raw_data # Already in desired list of dicts
                file_path_final = f"/reports_storage/{file_name_final}" # Placeholder
                file_size_final = len(json.dumps(formatted_output).encode('utf-8'))
                self.log_service.update_log_status_success(
                     self.db, log_entry.id, file_name_final, file_path_final, file_size_final,
                    int((datetime.utcnow() - start_time).total_seconds())
                )

            else: # PDF, XLSX etc.
                raise NotImplementedError(f"Output format {output_format} not yet supported.")

            self._audit_log(self.db, "REPORT_GENERATE_SUCCESS", "GeneratedReportLog", log_entry.id, f"Report '{report_def.report_name}' generated.", username)

        except Exception as e:
            error_msg = str(e)
            self.log_service.update_log_status_failed(
                self.db, log_entry.id, error_msg,
                int((datetime.utcnow() - start_time).total_seconds())
            )
            self._audit_log(self.db, "REPORT_GENERATE_FAIL", "GeneratedReportLog", log_entry.id, f"Report '{report_def.report_name}' generation failed: {error_msg}", username)
            # Do not re-raise HTTPException here as it's an async/background type process ideally.
            # The log entry reflects the failure. The API endpoint will return the log entry.

        db.refresh(log_entry) # Get final state of log entry
        return log_entry


# --- ScheduledReport Service ---
class ScheduledReportService(BaseReportingService):
    # CRUD, and methods to list upcoming runs, update next_run_at after execution
    # Actual execution trigger would be an external scheduler (Celery Beat, K8s CronJob)
    # calling an endpoint or a command that uses ReportGenerationService.
    def create_schedule(self, db: Session, sched_in: schemas.ScheduledReportCreate, user_id: int, username: str) -> models.ScheduledReport:
        # Validate report_definition_id
        if not ReportDefinitionService().get_definition_by_id(db, sched_in.report_definition_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report definition not found.")

        next_run = calculate_next_run(sched_in.cron_expression)

        db_sched = models.ScheduledReport(
            **sched_in.dict(exclude_unset=True, exclude={"parameters_values_json", "recipients_json"}),
            parameters_values_json=json.dumps(sched_in.parameters_values_json) if sched_in.parameters_values_json else None,
            recipients_json=json.dumps(sched_in.recipients_json) if sched_in.recipients_json else None,
            next_run_at=next_run,
            created_by_user_id=user_id
        )
        db.add(db_sched)
        db.commit()
        db.refresh(db_sched)
        self._audit_log(db, "SCHED_REPORT_CREATE", "ScheduledReport", db_sched.id, f"Scheduled report '{db_sched.schedule_name or db_sched.id}' created.", username)
        return db_sched

    def get_schedule_by_id(self, db: Session, sched_id: int) -> Optional[models.ScheduledReport]:
        return db.query(models.ScheduledReport).options(joinedload(models.ScheduledReport.report_definition)).filter(models.ScheduledReport.id == sched_id).first()

    def get_schedules(self, db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[models.ScheduledReport], int]:
        query = db.query(models.ScheduledReport).options(joinedload(models.ScheduledReport.report_definition))
        total = query.count()
        schedules = query.order_by(models.ScheduledReport.next_run_at.asc()).offset(skip).limit(limit).all()
        return schedules, total

    def update_schedule(self, db: Session, sched_id: int, sched_upd: schemas.ScheduledReportUpdate, username: str) -> Optional[models.ScheduledReport]:
        db_sched = self.get_schedule_by_id(db, sched_id)
        if not db_sched: return None

        update_data = sched_upd.dict(exclude_unset=True)
        cron_changed = False
        if "cron_expression" in update_data and update_data["cron_expression"] != db_sched.cron_expression:
            cron_changed = True

        for field, value in update_data.items():
             if value is not None:
                if field.endswith("_json") and value is not None:
                    setattr(db_sched, field, json.dumps(value))
                else:
                    setattr(db_sched, field, value)

        if cron_changed:
            db_sched.next_run_at = calculate_next_run(db_sched.cron_expression, db_sched.last_run_at or datetime.utcnow())

        db_sched.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_sched)
        self._audit_log(db, "SCHED_REPORT_UPDATE", "ScheduledReport", db_sched.id, f"Scheduled report '{db_sched.schedule_name or db_sched.id}' updated.", username)
        return db_sched

    def delete_schedule(self, db: Session, sched_id: int, username: str) -> bool:
        db_sched = self.get_schedule_by_id(db, sched_id)
        if not db_sched: return False
        self._audit_log(db, "SCHED_REPORT_DELETE", "ScheduledReport", db_sched.id, f"Scheduled report '{db_sched.schedule_name or db_sched.id}' deleted.", username)
        db.delete(db_sched)
        db.commit()
        return True

    def record_schedule_run(self, db: Session, sched_id: int, run_status: models.ReportStatusEnum, log_entry: Optional[models.GeneratedReportLog] = None, error_msg: Optional[str] = None):
        db_sched = self.get_schedule_by_id(db, sched_id)
        if db_sched:
            db_sched.last_run_at = datetime.utcnow()
            db_sched.last_run_status = run_status
            db_sched.last_error_message = error_msg if run_status == models.ReportStatusEnum.FAILED else None

            if db_sched.status != models.ScheduledReportStatusEnum.COMPLETED_ONCE: # Don't update next_run for one-off
                db_sched.next_run_at = calculate_next_run(db_sched.cron_expression, db_sched.last_run_at)

            if run_status == models.ReportStatusEnum.FAILED and db_sched.status == models.ScheduledReportStatusEnum.ACTIVE:
                db_sched.status = models.ScheduledReportStatusEnum.ERROR_STATE # Mark schedule as needing attention

            db.commit()
            # Audit this specific run via GeneratedReportLog or a dedicated schedule execution log.

# --- DashboardLayout Service ---
class DashboardLayoutService(BaseReportingService):
    # CRUD for dashboard layouts
    def create_layout(self, db: Session, layout_in: schemas.DashboardLayoutCreate, user_id: int, username: str) -> models.DashboardLayout:
        if layout_in.is_default: # Ensure only one default per user
            existing_default = db.query(models.DashboardLayout).filter(models.DashboardLayout.user_id == user_id, models.DashboardLayout.is_default == True).first()
            if existing_default:
                existing_default.is_default = False # Unset old default

        db_layout = models.DashboardLayout(
            user_id=user_id,
            dashboard_name=layout_in.dashboard_name,
            layout_config_json=json.dumps([w.dict() for w in layout_in.layout_config_json]), # Ensure widgets are dicts
            is_default=layout_in.is_default
        )
        db.add(db_layout)
        db.commit()
        db.refresh(db_layout)
        self._audit_log(db, "DASH_LAYOUT_CREATE", "DashboardLayout", db_layout.id, f"Dashboard '{db_layout.dashboard_name}' created.", username)
        return db_layout

    def get_layout_by_id(self, db: Session, layout_id: int, user_id: int) -> Optional[models.DashboardLayout]: # User ID for auth
        return db.query(models.DashboardLayout).filter(models.DashboardLayout.id == layout_id, models.DashboardLayout.user_id == user_id).first()

    def get_layouts_for_user(self, db: Session, user_id: int) -> List[models.DashboardLayout]:
        return db.query(models.DashboardLayout).filter(models.DashboardLayout.user_id == user_id).order_by(models.DashboardLayout.dashboard_name).all()

    def get_default_layout_for_user(self, db: Session, user_id: int) -> Optional[models.DashboardLayout]:
        return db.query(models.DashboardLayout).filter(models.DashboardLayout.user_id == user_id, models.DashboardLayout.is_default == True).first()


    def update_layout(self, db: Session, layout_id: int, layout_upd: schemas.DashboardLayoutUpdate, user_id: int, username: str) -> Optional[models.DashboardLayout]:
        db_layout = self.get_layout_by_id(db, layout_id, user_id)
        if not db_layout: return None

        if layout_upd.is_default == True and not db_layout.is_default: # Setting new default
            existing_default = db.query(models.DashboardLayout).filter(models.DashboardLayout.user_id == user_id, models.DashboardLayout.is_default == True, models.DashboardLayout.id != layout_id).first()
            if existing_default:
                existing_default.is_default = False

        update_data = layout_upd.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "layout_config_json":
                    setattr(db_layout, field, json.dumps([w.dict() for w in value]))
                else:
                    setattr(db_layout, field, value)

        db_layout.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_layout)
        self._audit_log(db, "DASH_LAYOUT_UPDATE", "DashboardLayout", db_layout.id, f"Dashboard '{db_layout.dashboard_name}' updated.", username)
        return db_layout

    def delete_layout(self, db: Session, layout_id: int, user_id: int, username: str) -> bool:
        db_layout = self.get_layout_by_id(db, layout_id, user_id)
        if not db_layout: return False
        if db_layout.is_default:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default dashboard. Set another as default first.")

        self._audit_log(db, "DASH_LAYOUT_DELETE", "DashboardLayout", db_layout.id, f"Dashboard '{db_layout.dashboard_name}' deleted.", username)
        db.delete(db_layout)
        db.commit()
        return True

# Instantiate services
report_definition_service = ReportDefinitionService()
generated_report_log_service = GeneratedReportLogService()
# ReportGenerationService needs db, log_service, def_service passed on instantiation or method call
scheduled_report_service = ScheduledReportService()
dashboard_layout_service = DashboardLayoutService()
