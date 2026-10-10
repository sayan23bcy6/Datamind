from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_dataset_creates_dataset_and_version() -> None:
    csv_data = b"customer_id,name,amount\n1,Alice,$10.50\n2,Bob,$20.00\n3,Charlie,$15.25\n"

    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample.csv", csv_data, "text/csv")},
        data={"dataset_name": "demo-upload"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["dataset_name"] == "demo-upload"
    assert payload["row_count"] == 3
    assert payload["column_count"] == 3
    assert payload["version_id"]
