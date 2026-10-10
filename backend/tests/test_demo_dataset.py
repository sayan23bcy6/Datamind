from pathlib import Path

from app.services.demo_dataset import generate_demo_dataset


def test_generate_demo_dataset_creates_reasonable_csv(tmp_path: Path) -> None:
    metadata = generate_demo_dataset(output_dir=tmp_path, name="customer_demo.csv")

    output_file = Path(metadata["path"])
    assert output_file.exists()
    assert metadata["rows"] > 10
    assert metadata["columns"] > 5
    assert "country" in metadata["problem_columns"]
