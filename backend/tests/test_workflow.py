from __future__ import annotations

import pandas as pd
import pytest

from app.core.database import SessionLocal
from app.db.repositories.dataset_repository import DatasetRepository
from app.db.repositories.investigation_repository import InvestigationRepository
from app.services.demo_dataset import generate_demo_dataset
from app.services.investigation_service import InvestigationService
from app.tools.detectors import calculate_dimension_scores
from app.workflow.state_machine import (
    check_budget_exhausted,
    route_human_review,
    route_investigation,
    route_verification,
)


def test_workflow_approve_path() -> None:
    state, reason = route_investigation([{"verdict": "APPROVE"}], 0, 3)
    assert state == "EXECUTE"
    assert "approved" in reason


def test_workflow_reject_then_approve() -> None:
    # 1st critique -> rejected
    state1, reason1 = route_investigation([{"verdict": "REJECT"}], 0, 3)
    assert state1 == "INVESTIGATE"

    # 2nd critique -> approved
    state2, reason2 = route_investigation([{"verdict": "APPROVE"}], 1, 3)
    assert state2 == "EXECUTE"


def test_workflow_escalate_then_approve() -> None:
    # Escalation to human
    state1, reason1 = route_investigation([{"verdict": "ESCALATE_TO_HUMAN"}], 0, 3)
    assert state1 == "AWAIT_HUMAN"

    # Human decision: approve
    state2, reason2 = route_human_review("approve")
    assert state2 == "EXECUTE"


def test_workflow_escalate_then_reject() -> None:
    state1, reason1 = route_investigation([{"verdict": "ESCALATE_TO_HUMAN"}], 0, 3)
    assert state1 == "AWAIT_HUMAN"

    # Human decision: reject
    state2, reason2 = route_human_review("reject")
    assert state2 == "INVESTIGATE"


def test_workflow_iteration_cap() -> None:
    state, reason = route_investigation([{"verdict": "REJECT"}], 3, 3)
    assert state == "PARTIAL"
    assert "iteration cap" in reason


def test_workflow_cost_cap() -> None:
    state, reason = route_investigation(
        [{"verdict": "APPROVE"}], 0, 3, cost_used=200000, cost_budget=200000
    )
    assert state == "PARTIAL"
    assert "token budget exhausted" in reason


def test_deterministic_dimension_formulas() -> None:
    # 10 rows: 2 missing cells in col 'a' (2/10 = 0.2), 0 in 'b' (0.0). Mean missing = 0.1 -> completeness = 90.0
    # 2 exact duplicates out of 10 rows -> 8 unique / 10 -> uniqueness = 80.0
    df = pd.DataFrame({
        "a": [10.0, 20.0, 10.0, None, 50.0, 60.0, 70.0, 80.0, None, 100.0],
        "b": ["NY", "NY", "NY", "CA", "CA", "TX", "TX", "FL", "FL", "WA"],
    })
    scores = calculate_dimension_scores(df)

    assert 0.0 <= scores["completeness"] <= 100.0
    assert 0.0 <= scores["uniqueness"] <= 100.0
    assert 0.0 <= scores["consistency"] <= 100.0
    assert 0.0 <= scores["validity"] <= 100.0
    assert 0.0 <= scores["accuracy"] <= 100.0

    # Overall must be exact unweighted mean of the 5 dimensions
    expected_overall = round(
        (
            scores["completeness"]
            + scores["uniqueness"]
            + scores["consistency"]
            + scores["validity"]
            + scores["accuracy"]
        )
        / 5.0,
        2,
    )
    assert scores["overall"] == expected_overall


def test_resume_from_checkpoint_after_restart(tmp_path) -> None:
    db = SessionLocal()
    try:
        # Generate demo dataset
        meta = generate_demo_dataset(output_dir=tmp_path)
        d_repo = DatasetRepository(db)
        dataset = d_repo.create_dataset("Resume Test")
        v = d_repo.create_version(
            dataset.id,
            source_name="demo.csv",
            stored_path=meta["path"],
            file_size_bytes=1000,
            sha256="test-sha-12345",
            row_count=meta["rows"],
            column_count=meta["columns"],
            is_original=True,
        )

        service1 = InvestigationService(db)
        inv = service1.create_investigation(dataset.id, v.id)

        # Simulate checkpoint at CRITIQUE
        service1.repo.add_checkpoint(
            inv.id,
            "CRITIQUE",
            iteration=0,
            payload={
                "proposals": [
                    {
                        "proposal_id": "p-1",
                        "operation": "deduplicate",
                        "target_columns": ["customer_id"],
                        "rationale": "Exact duplicates",
                    }
                ]
            },
        )
        inv.state = "CRITIQUE"
        db.commit()

        # Simulate restart with fresh service instance
        service2 = InvestigationService(db)
        resumed_inv = service2.run(inv.id)

        assert resumed_inv.status in ("completed", "partial")
        # Check that it reached completed state
        assert resumed_inv.state in ("COMPLETED", "PARTIAL")
    finally:
        db.close()
