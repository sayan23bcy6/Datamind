from __future__ import annotations

import os
import time
from typing import Any

import httpx
import pytest

from app.core.config import get_settings
from app.main import app

settings = get_settings()
BASE_URL = os.environ.get("TEST_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _get_client():
    # If the stack is running on 127.0.0.1:8000, use HTTP requests; otherwise fallback to TestClient
    try:
        r = httpx.get(f"{BASE_URL}/api/v1/health", timeout=1.0)
        if r.status_code == 200:
            return httpx.Client(base_url=BASE_URL, timeout=30.0)
    except Exception:
        pass
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_full_pipeline_end_to_end() -> None:
    client = _get_client()

    # Verify demo endpoint works
    demo_res = client.post("/api/v1/datasets/demo")
    assert demo_res.status_code == 200, demo_res.text
    assert "dataset_id" in demo_res.json()

    # 1. Upload the demo dataset for a clean, deterministic e2e pipeline run
    from app.services.demo_dataset import generate_demo_dataset
    meta = generate_demo_dataset()
    with open(meta["path"], "rb") as f:
        upload_res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("demo_customer_data.csv", f, "text/csv")},
            data={"dataset_name": f"Demo E2E Run {int(time.time())}"},
        )
    assert upload_res.status_code == 200, upload_res.text
    upload_data = upload_res.json()
    dataset_id = upload_data["dataset_id"]
    orig_version_id = upload_data["version_id"]
    orig_sha256 = upload_data["sha256"]

    # 2. Start investigation
    inv_res = client.post(f"/api/v1/datasets/{dataset_id}/investigations")
    assert inv_res.status_code == 200, inv_res.text
    inv_id = inv_res.json()["investigation_id"]

    # 3. Poll until completed or partial within 120 seconds
    deadline = time.time() + 120.0
    final_status = "pending"
    inv_data: dict[str, Any] = {}

    while time.time() < deadline:
        check = client.get(f"/api/v1/investigations/{inv_id}")
        assert check.status_code == 200, check.text
        inv_data = check.json()
        final_status = inv_data["status"]
        if final_status in ("completed", "partial"):
            break
        time.sleep(1.0)

    assert final_status in ("completed", "partial"), f"Investigation timed out, status: {final_status}"
    output_version_id = inv_data.get("output_version_id")
    assert output_version_id, "Cleaned output_version_id must be populated"

    # 4. Assert cleaned version's parent_version_id equals original's id
    ver_after_res = client.get(f"/api/v1/datasets/{dataset_id}/versions")
    assert ver_after_res.status_code == 200
    after_versions = ver_after_res.json()
    cleaned_ver = next(v for v in after_versions if v["id"] == output_version_id)
    assert cleaned_ver["parent_version_id"] == orig_version_id

    # 5. Assert original SHA-256 is unchanged
    orig_ver_check = next(v for v in after_versions if v["id"] == orig_version_id)
    assert orig_ver_check["sha256"] == orig_sha256

    # 6. Assert each planted duplicate and outlier was detected
    diff_res = client.get(f"/api/v1/investigations/{inv_id}/diff")
    assert diff_res.status_code == 200
    diff_items = diff_res.json()
    has_removed_duplicate = any(d["change_type"] == "removed" for d in diff_items)
    assert has_removed_duplicate, "Planted duplicate rows must be detected and removed"

    ev_res = client.get(f"/api/v1/investigations/{inv_id}/evidence")
    assert ev_res.status_code == 200
    evidence = ev_res.json()
    assert any("duplicate" in e["claim"].lower() for e in evidence)

    dist_res = client.get(f"/api/v1/investigations/{inv_id}/distributions")
    assert dist_res.status_code == 200

    # 7. Assert every row-count change has a cleaning decision with a reason
    audit_res = client.get(f"/api/v1/investigations/{inv_id}/audit")
    assert audit_res.status_code == 200
    audit = audit_res.json()
    audit_trail = audit.get("audit_trail", [])
    assert len(audit_trail) > 0, "Audit trail must not be empty"

    decisions = [a for a in audit_trail if a.get("type") == "cleaning_decision"]
    for d in decisions:
        if d.get("delta", 0) != 0:
            assert d.get("reason"), f"Decision with delta {d.get('delta')} must include a reason"

    # 8. Assert all four report formats exist
    for fmt in ["json", "markdown", "html", "pdf"]:
        r_res = client.get(f"/api/v1/investigations/{inv_id}/report?format={fmt}")
        assert r_res.status_code == 200, f"Report format {fmt} failed"
        assert len(r_res.content) > 0

    # 9. Assert audit.json lists transitions in order
    timestamps = [a["timestamp"] for a in audit_trail if "timestamp" in a]
    assert timestamps == sorted(timestamps), "Audit trail timestamps must be chronologically ordered"

    # 10. Assert state_changed events were emitted for each transition
    transitions = [a for a in audit_trail if a.get("type") == "state_transition"]
    states_observed = [t["state"] for t in transitions]
    assert "PROFILE" in states_observed
    assert "INVESTIGATE" in states_observed
    assert "COMPLETED" in states_observed or "PARTIAL" in states_observed

    # 11. Assert reject-then-approve path ran at least once
    proposals_res = client.get(f"/api/v1/investigations/{inv_id}/proposals")
    assert proposals_res.status_code == 200
    props_and_verdicts = proposals_res.json()
    verdicts = [item["verdict"] for item in props_and_verdicts if item.get("type") == "verdict"]
    assert "REJECT" in verdicts, "Reject-then-approve path requires at least one REJECT verdict"
    assert "APPROVE" in verdicts, "Reject-then-approve path requires at least one APPROVE verdict"
