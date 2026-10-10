from __future__ import annotations

import io
from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_api_contracts_end_to_end() -> None:
    # 1. GET /health
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    h_data = health_res.json()
    for field in ["status", "service", "environment", "postgres", "redis"]:
        assert field in h_data

    # 2. POST /datasets/demo
    demo_res = client.post("/api/v1/datasets/demo")
    assert demo_res.status_code == 200
    demo_data = demo_res.json()
    for field in ["dataset_id", "version_id", "message", "created"]:
        assert field in demo_data
    dataset_id = demo_data["dataset_id"]
    version_id = demo_data["version_id"]

    # Calling it a second time returns created == False
    demo_res_second = client.post("/api/v1/datasets/demo")
    assert demo_res_second.status_code == 200
    assert demo_res_second.json()["created"] is False

    # 3. POST /datasets/upload
    csv_bytes = b"col1,col2\n10,20\n30,40\n"
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("test_upload.csv", csv_bytes, "text/csv")},
        data={"dataset_name": "Contract Upload"},
    )
    assert upload_res.status_code == 200
    u_data = upload_res.json()
    for field in ["dataset_id", "version_id", "dataset_name", "file_name", "row_count", "column_count", "sha256"]:
        assert field in u_data

    # 4. GET /datasets
    datasets_res = client.get("/api/v1/datasets")
    assert datasets_res.status_code == 200
    datasets = datasets_res.json()
    assert isinstance(datasets, list) and len(datasets) > 0
    for field in ["id", "name", "created_at"]:
        assert field in datasets[0]

    # 5. GET /datasets/{dataset_id}/versions
    versions_res = client.get(f"/api/v1/datasets/{dataset_id}/versions")
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert isinstance(versions, list) and len(versions) > 0
    for field in [
        "id", "version_number", "parent_version_id", "source_name",
        "row_count", "column_count", "file_size_bytes", "sha256", "is_original", "created_at"
    ]:
        assert field in versions[0]

    # 6. GET /versions/{version_id}/profile
    prof_res = client.get(f"/api/v1/versions/{version_id}/profile")
    assert prof_res.status_code == 200
    prof = prof_res.json()
    for field in ["row_count", "column_count", "columns", "dimensions"]:
        assert field in prof
    for col in prof["columns"]:
        for field in ["name", "dtype", "missing_count", "missing_rate", "unique_count", "sample_values"]:
            assert field in col
    for dim in ["completeness", "uniqueness", "consistency", "validity", "accuracy", "overall"]:
        assert dim in prof["dimensions"]

    # 7. GET /versions/{version_id}/download
    dl_res = client.get(f"/api/v1/versions/{version_id}/download")
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0

    # 8. POST /datasets/{dataset_id}/investigations
    inv_create_res = client.post(f"/api/v1/datasets/{dataset_id}/investigations")
    assert inv_create_res.status_code == 200
    inv_create = inv_create_res.json()
    assert "investigation_id" in inv_create
    assert "status" in inv_create
    inv_id = inv_create["investigation_id"]

    # 9. GET /investigations/{id}
    inv_res = client.get(f"/api/v1/investigations/{inv_id}")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    for field in [
        "investigation_id", "status", "state", "iteration", "max_iterations",
        "cost_used", "cost_budget", "dataset_version_id", "output_version_id", "error"
    ]:
        assert field in inv_data

    # 10. GET /investigations/{id}/proposals
    prop_res = client.get(f"/api/v1/investigations/{inv_id}/proposals")
    assert prop_res.status_code == 200
    assert isinstance(prop_res.json(), list)

    # 11. GET /investigations/{id}/diff
    diff_res = client.get(f"/api/v1/investigations/{inv_id}/diff")
    assert diff_res.status_code == 200
    assert isinstance(diff_res.json(), list)

    # 12. GET /investigations/{id}/distributions
    dist_res = client.get(f"/api/v1/investigations/{inv_id}/distributions")
    assert dist_res.status_code == 200
    assert isinstance(dist_res.json(), list)

    # 13. GET /investigations/{id}/evidence
    ev_res = client.get(f"/api/v1/investigations/{inv_id}/evidence")
    assert ev_res.status_code == 200
    assert isinstance(ev_res.json(), list)

    # Ensure completed for report generation contract check
    from app.core.database import SessionLocal
    from app.services.investigation_service import InvestigationService
    _db = SessionLocal()
    _service = InvestigationService(_db)
    _service.run(inv_id)
    _db.close()

    # 14. GET /investigations/{id}/report formats
    for fmt in ["json", "markdown", "html", "pdf"]:
        rep_res = client.get(f"/api/v1/investigations/{inv_id}/report?format={fmt}")
        assert rep_res.status_code == 200, f"Failed format {fmt}"

    # 15. GET /investigations/{id}/audit
    audit_res = client.get(f"/api/v1/investigations/{inv_id}/audit")
    assert audit_res.status_code == 200

    # 16. GET /investigations/{id}/events
    events_res = client.get(f"/api/v1/investigations/{inv_id}/events")
    assert events_res.status_code == 200
    assert "text/event-stream" in events_res.headers.get("content-type", "")

    # 17. Reviews and Decisions
    from app.core.database import SessionLocal
    from app.db.repositories.investigation_repository import InvestigationRepository
    db = SessionLocal()
    r_repo = InvestigationRepository(db)
    test_rev = r_repo.add_review(
        inv_id,
        proposal_id="test-prop",
        proposal_summary="Contract proposal review",
        parameters={"keep": "first"},
        status="pending",
    )
    db.close()

    revs_res = client.get("/api/v1/reviews?status=pending")
    assert revs_res.status_code == 200
    pending_revs = revs_res.json()
    assert isinstance(pending_revs, list) and len(pending_revs) > 0
    for field in ["review_id", "investigation_id", "proposal_id", "status", "proposal_summary", "parameters"]:
        assert field in pending_revs[0]

    dec_res = client.post(
        f"/api/v1/reviews/{test_rev.id}/decision",
        json={"decision": "approve"},
    )
    assert dec_res.status_code == 200

    # 18. Watches
    watch_res = client.post(
        "/api/v1/watches",
        json={"dataset_id": dataset_id, "schedule": "@daily", "drift_threshold": "0.15", "enabled": True},
    )
    assert watch_res.status_code == 200
    w_data = watch_res.json()
    for field in ["id", "dataset_id", "schedule", "drift_threshold", "enabled", "last_checked_at", "created_at"]:
        assert field in w_data
    w_id = w_data["id"]

    watches_list = client.get("/api/v1/watches")
    assert watches_list.status_code == 200
    assert any(w["id"] == w_id for w in watches_list.json())

    del_res = client.delete(f"/api/v1/watches/{w_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
