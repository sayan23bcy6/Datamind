from __future__ import annotations

import os
import time

import pandas as pd
from fastapi.testclient import TestClient

from app.agents.providers import MockProvider
from app.core.config import get_settings
from app.tools.detectors import detect_duplicates, detect_outliers, standardize_format
from app.workflow.state_machine import route_investigation
from app.main import app

client = TestClient(app)


def test_demo_dataset_upload_and_investigation() -> None:
    response = client.post("/api/v1/datasets/demo")
    assert response.status_code == 200, response.text
    payload = response.json()
    dataset_id = payload["dataset_id"]
    assert dataset_id

    investigation_response = client.post(f"/api/v1/datasets/{dataset_id}/investigations")
    assert investigation_response.status_code == 200, investigation_response.text
    investigation_id = investigation_response.json()["investigation_id"]

    for _ in range(30):
        state = client.get(f"/api/v1/investigations/{investigation_id}")
        status = state.json()["status"]
        if status in {"completed", "partial"}:
            break
        time.sleep(0.2)

    final = client.get(f"/api/v1/investigations/{investigation_id}")
    assert final.json()["status"] in {"completed", "partial"}, final.text

    report = client.get(f"/api/v1/investigations/{investigation_id}/report?format=json")
    assert report.status_code == 200

    events = client.get(f"/api/v1/investigations/{investigation_id}/events")
    assert events.status_code == 200
    assert "text/event-stream" in events.headers.get("content-type", "")


def test_known_answer_tools() -> None:
    df = pd.DataFrame({
        "customer_id": ["C-1", "C-1", "C-2", "C-3"],
        "country": ["NY", "New York", "new york ", "CA"],
    })
    duplicate_info = detect_duplicates(df)
    assert duplicate_info["exact_duplicate_rows"]

    outlier_df = pd.DataFrame({"amount": [10, 12, 11, 13, 15, 100]})
    outlier_info = detect_outliers(outlier_df)
    assert outlier_info["findings"]

    cleaned = standardize_format(df, "country")
    assert "new york" in cleaned["country"].str.lower().tolist()


def test_workflow_routing_logic() -> None:
    assert route_investigation([{"verdict": "APPROVE"}], 0, 3, 0, 100) == ("EXECUTE", "all proposals approved")
    assert route_investigation([{"verdict": "REJECT"}], 0, 3, 0, 100) == ("INVESTIGATE", "rejected proposals require another investigation pass")
    assert route_investigation([{"verdict": "ESCALATE_TO_HUMAN"}], 0, 3, 0, 100) == ("AWAIT_HUMAN", "escalated for human review")


def test_mock_provider_reject_then_approve_sequence() -> None:
    provider = MockProvider()
    first = provider.generate_structured(dict, "critique the proposal", [])
    second = provider.generate_structured(dict, "critique the proposal", [])
    first_verdict = first["verdict"] if isinstance(first, dict) else first[0]["verdict"]
    second_verdict = second["verdict"] if isinstance(second, dict) else second[0]["verdict"]
    assert first_verdict == "REJECT"
    assert second_verdict == "APPROVE"
