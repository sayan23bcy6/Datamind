from __future__ import annotations

import pandas as pd
from hypothesis import given, strategies as st
import pytest

from app.services.demo_dataset import generate_demo_dataset
from app.tools.detectors import (
    deduplicate,
    detect_duplicates,
    detect_outliers,
    standardize_format,
)


def test_planted_duplicate_found(tmp_path) -> None:
    meta = generate_demo_dataset(output_dir=tmp_path)
    df = pd.read_csv(meta["path"])
    dupes = detect_duplicates(df)
    assert len(dupes["exact_duplicate_rows"]) >= 2
    # Verify exact planted duplicate rows (e.g., row 2 duplicates row 0)
    assert 2 in dupes["exact_duplicate_rows"] or 8 in dupes["exact_duplicate_rows"]


def test_planted_outlier_flagged(tmp_path) -> None:
    meta = generate_demo_dataset(output_dir=tmp_path)
    df = pd.read_csv(meta["path"])
    outliers = detect_outliers(df)
    findings = outliers.get("findings", [])
    assert len(findings) > 0
    # Confirm planted outlier values (e.g., 99999.0, 125000.5, 88888.0)
    found_values = []
    for f in findings:
        found_values.extend(f.get("outlier_values", []))
    assert any(v >= 80000.0 for v in found_values)


def test_label_variants_map_to_canonical() -> None:
    df = pd.DataFrame({"state": ["NY", "New York", "new york ", "CA", "California", "ca ", "TX"]})
    cleaned = standardize_format(df, "state")
    assert cleaned["state"].tolist() == [
        "New York",
        "New York",
        "New York",
        "California",
        "California",
        "California",
        "Texas",
    ]


def test_dates_normalize_to_iso8601() -> None:
    df = pd.DataFrame({
        "signup_date": ["2024/01/15", "02-18-2024", "2024-03-22", "04/05/2024"]
    })
    cleaned = standardize_format(df, "signup_date")
    assert cleaned["signup_date"].tolist() == [
        "2024-01-15",
        "2024-02-18",
        "2024-03-22",
        "2024-04-05",
    ]


# Hypothesis tests
@given(st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- /$,.", max_size=20), min_size=1, max_size=30))
def test_hypothesis_standardize_format_is_idempotent(text_list: list[str]) -> None:
    df = pd.DataFrame({"col": text_list})
    first_pass = standardize_format(df, "col")
    second_pass = standardize_format(first_pass, "col")
    pd.testing.assert_frame_equal(first_pass, second_pass)


@given(st.lists(st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=30))
def test_hypothesis_no_row_count_change_without_decision(int_list: list[int]) -> None:
    df = pd.DataFrame({"num": int_list, "cat": [f"val_{x % 5}" for x in range(len(int_list))]})
    # Non-deduplication tools must strictly preserve row count
    std = standardize_format(df, "cat")
    assert len(std) == len(df)

    # When deduplicate changes row count, it returns the removed row indices
    cleaned, removed = deduplicate(df)
    assert len(cleaned) + len(removed) == len(df)
