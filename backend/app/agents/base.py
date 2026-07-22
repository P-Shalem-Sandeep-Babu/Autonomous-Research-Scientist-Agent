import logging
from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import ResearchStage, Project

logger = logging.getLogger("arsa.agents")

class BaseAgent:
    def __init__(self, db: Session, project_id: int, stage_name: str):
        self.db = db
        self.project_id = project_id
        self.stage_name = stage_name
        self.stage_record = None
        self.logs_list = []
        
    def _get_or_create_stage(self) -> ResearchStage:
        stage = self.db.query(ResearchStage).filter(
            ResearchStage.project_id == self.project_id,
            ResearchStage.stage_name == self.stage_name
        ).first()
        
        if not stage:
            stage = ResearchStage(
                project_id=self.project_id,
                stage_name=self.stage_name,
                status="pending"
            )
            self.db.add(stage)
            self.db.commit()
            self.db.refresh(stage)
        
        self.stage_record = stage
        return stage

    def start_stage(self):
        stage = self._get_or_create_stage()
        stage.status = "active"
        stage.started_at = datetime.utcnow()
        stage.output_data = {"logs": []}
        stage.reasoning_chain = []
        self.db.commit()
        self.db.refresh(stage)
        self.log(f"Starting {self.stage_name.replace('_', ' ').title()} Stage...")

    def reason_step(self, message: str, step_type: str = "thought"):
        timestamp = datetime.utcnow().isoformat()
        step_entry = {"timestamp": timestamp, "type": step_type, "message": message, "stage": self.stage_name}
        print(f"[{self.stage_name.upper()} - REASONING ({step_type.upper()})] {message}")
        if self.stage_record:
            stage = self.db.query(ResearchStage).get(self.stage_record.id)
            if stage:
                chain = list(stage.reasoning_chain or [])
                chain.append(step_entry)
                stage.reasoning_chain = chain
                self.db.commit()
                # Notify active listeners if callback is registered (e.g. websocket)
                if hasattr(self, 'on_reasoning_callback') and self.on_reasoning_callback:
                    self.on_reasoning_callback(step_entry)


    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.utcnow().isoformat()
        log_entry = {"timestamp": timestamp, "level": level, "message": message}
        self.logs_list.append(log_entry)
        
        # Print locally
        try:
            print(f"[{self.stage_name.upper()} - {level}] {message}")
        except UnicodeEncodeError:
            safe_message = message.encode('ascii', errors='replace').decode('ascii')
            print(f"[{self.stage_name.upper()} - {level}] {safe_message}")
        
        # Save logs dynamically in the active stage's JSON output
        if self.stage_record:
            # We fetch a fresh DB session query to avoid cache/threading conflicts
            stage = self.db.query(ResearchStage).get(self.stage_record.id)
            if stage:
                output = dict(stage.output_data or {})
                logs = list(output.get("logs", []))
                logs.append(log_entry)
                output["logs"] = logs
                stage.output_data = output
                self.db.commit()
                # Notify active listeners if callback is registered (done by manager)
                if hasattr(self, 'on_log_callback') and self.on_log_callback:
                    self.on_log_callback(log_entry)
                    
    def complete_stage(self, output_payload: dict):
        if self.stage_record:
            stage = self.db.query(ResearchStage).get(self.stage_record.id)
            if stage:
                output = dict(stage.output_data or {})
                output.update(output_payload)
                stage.output_data = output
                stage.status = "completed"
                stage.completed_at = datetime.utcnow()
                self.db.commit()
                self.log(f"Completed {self.stage_name.replace('_', ' ').title()} Stage successfully.")

    def fail_stage(self, error_message: str):
        if self.stage_record:
            stage = self.db.query(ResearchStage).get(self.stage_record.id)
            if stage:
                output = dict(stage.output_data or {})
                output["error"] = error_message
                stage.output_data = output
                stage.status = "failed"
                stage.completed_at = datetime.utcnow()
                self.db.commit()
                self.log(f"Stage failed: {error_message}", "ERROR")

    async def execute(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement the execute method")
