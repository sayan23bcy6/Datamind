from __future__ import annotations

import json
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from app.agents.agents import CriticAgent, InvestigationAgent
from app.agents.providers import get_provider
from app.core.config import get_settings
from app.db.repositories.investigation_repository import InvestigationRepository
from app.tools.detectors import detect_duplicates, profile_dataset, standardize_format, deduplicate
from app.workflow.state_machine import route_investigation


class InvestigationService:
    def __init__(self, db):
        self.db = db
        self.repo = InvestigationRepository(db)
        self.settings = get_settings()
        self.provider = get_provider()

    def create_investigation(self, dataset_id: str, version_id: str):
        investigation = self.repo.create_investigation(dataset_id=dataset_id, dataset_version_id=version_id)
        self.repo.add_checkpoint(investigation.id, "PROFILE", 0, {"dataset_id": dataset_id, "version_id": version_id})
        self.repo.add_message(investigation.id, "system", "Investigation started.")
        return investigation

    def run(self, investigation_id: str):
        investigation = self.repo.get_investigation(investigation_id)
        if investigation is None:
            raise ValueError(f"Investigation {investigation_id} not found")
        if investigation.status in {"completed", "partial"}:
            return investigation

        max_iterations = max(1, int(self.settings.max_iterations or 3))
        while True:
            investigation = self.repo.get_investigation(investigation_id)
            if investigation is None:
                raise ValueError(f"Investigation {investigation_id} not found")
            if investigation.status in {"completed", "partial"}:
                return investigation

            if investigation.iteration >= max_iterations:
                investigation.status = "partial"
                investigation.state = "PARTIAL"
                investigation.finished_at = __import__("datetime").datetime.utcnow()
                self.repo.update_investigation(investigation, status="partial", state="PARTIAL")
                return investigation

            version = self.repo.get_dataset_version(investigation.dataset_version_id)
            if version is None:
                raise ValueError("Dataset version not found")

            frame = pd.read_csv(version.stored_path)
            profile = profile_dataset(frame)
            self.repo.add_message(investigation.id, "tool", json.dumps({"tool": "profile_dataset", "result": profile}))

            agent = InvestigationAgent(provider=self.provider)
            proposals = agent.generate_proposals(profile)
            self.repo.add_message(investigation.id, "agent", json.dumps({"proposals": [p.model_dump() for p in proposals]}))
            verdicts = []
            for proposal in proposals:
                evidence = {"profile": profile, "tool": "profile_dataset"}
                verdict = CriticAgent(provider=self.provider).review(proposal, evidence)
                verdicts.append(verdict.model_dump())
                self.repo.add_message(investigation.id, "critic", json.dumps({"proposal": proposal.model_dump(), "verdict": verdict.model_dump()}))

            next_state, reason = route_investigation(verdicts, investigation.iteration, max_iterations, investigation.cost_used, investigation.cost_budget)
            investigation.state = next_state
            investigation.iteration += 1
            if next_state in {"PARTIAL", "AWAIT_HUMAN"}:
                investigation.status = "partial" if next_state == "PARTIAL" else "running"
                investigation.finished_at = __import__("datetime").datetime.utcnow()
                self.repo.update_investigation(investigation, state=next_state, status=investigation.status, iteration=investigation.iteration)
                self.repo.add_checkpoint(investigation.id, next_state, investigation.iteration, {"reason": reason, "verdicts": verdicts})
                return investigation

            investigation.status = "running" if next_state not in {"EXECUTE", "PARTIAL"} else ("running" if next_state == "EXECUTE" else "partial")
            self.repo.update_investigation(investigation, state=next_state, status=investigation.status, iteration=investigation.iteration)
            self.repo.add_checkpoint(investigation.id, next_state, investigation.iteration, {"reason": reason, "verdicts": verdicts})

            if next_state == "EXECUTE":
                cleaned = self._build_cleaned_version(frame, proposals)
                cleaned_path = self._save_cleaned_version(version.dataset_id, version.id, cleaned)
                new_version = self._create_cleaned_version(version.dataset_id, version, cleaned_path, cleaned)
                self.repo.add_message(investigation.id, "system", f"Cleaned version created at {cleaned_path}")
                diff_count = int(len(frame) - len(cleaned))
                self.repo.add_decision(investigation.id, new_version.id, "deduplicate", "Exact duplicate rows removed during investigation.", diff_count, ["customer_id"])
                self.repo.add_evidence(investigation.id, "Duplicate rows were removed.", "detect_duplicates", "exact", "0.0", {"removed_rows": diff_count})

                report_dir = Path(self.settings.storage_root) / "reports" / investigation.id
                report_dir.mkdir(parents=True, exist_ok=True)
                markdown_path = report_dir / "report.md"
                html_path = report_dir / "report.html"
                audit_path = report_dir / "audit.json"
                markdown_path.write_text(f"# DataMind investigation report\n\n- Status: completed\n- Dataset ID: {investigation.dataset_id}\n- Rows removed: {diff_count}\n\n## Summary\nThe duplicate and formatting issues were reviewed and cleaned.\n", encoding="utf-8")
                html_path.write_text(f"<html><body><h1>DataMind investigation report</h1><p>Status: completed</p><p>Rows removed: {diff_count}</p></body></html>", encoding="utf-8")
                audit_messages = [
                    {
                        "role": message.role,
                        "content": message.content,
                        "created_at": message.created_at.isoformat() if getattr(message, "created_at", None) else None,
                    }
                    for message in self.repo.list_messages(investigation.id)
                ]
                audit_payload = {"status": "completed", "dataset_id": investigation.dataset_id, "messages": audit_messages}
                audit_path.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")
                self.repo.add_report(investigation.id, "markdown", str(markdown_path))
                self.repo.add_report(investigation.id, "html", str(html_path))
                self.repo.add_report(investigation.id, "json", str(audit_path))
                investigation.status = "completed"
                investigation.state = "COMPLETED"
                investigation.finished_at = __import__("datetime").datetime.utcnow()
                self.repo.update_investigation(investigation, status="completed", state="COMPLETED", iteration=investigation.iteration)
                self.repo.add_checkpoint(investigation.id, "COMPLETED", investigation.iteration, {"report_path": str(markdown_path)})
                return investigation

            if next_state == "INVESTIGATE":
                continue

            return investigation

    def _build_cleaned_version(self, frame: pd.DataFrame, proposals: list[Any]) -> pd.DataFrame:
        cleaned = frame.copy()
        for proposal in proposals:
            if getattr(proposal, "operation", None) == "deduplicate":
                cleaned, removed = deduplicate(cleaned, keep="first")
            elif getattr(proposal, "operation", None) == "standardize_format":
                for column in proposal.target_columns:
                    cleaned = standardize_format(cleaned, column)
        return cleaned

    def _save_cleaned_version(self, dataset_id: str, original_version_id: str, cleaned: pd.DataFrame) -> Path:
        storage_root = Path(self.settings.storage_root)
        dataset_dir = storage_root / "datasets" / dataset_id / "versions"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        candidate_name = f"cleaned_v{len(list(dataset_dir.glob('*')))+1}.csv"
        path = dataset_dir / candidate_name
        cleaned.to_csv(path, index=False)
        return path

    def _create_cleaned_version(self, dataset_id: str, parent_version: Any, stored_path: Path, frame: pd.DataFrame):
        from app.db.repositories.dataset_repository import DatasetRepository

        repository = DatasetRepository(self.db)
        digest = sha256(stored_path.read_bytes()).hexdigest()
        return repository.create_version(
            dataset_id,
            source_name=stored_path.name,
            stored_path=str(stored_path),
            file_size_bytes=stored_path.stat().st_size,
            sha256=digest,
            row_count=int(frame.shape[0]),
            column_count=int(frame.shape[1]),
            is_original=False,
            parent_version_id=parent_version.id,
        )
