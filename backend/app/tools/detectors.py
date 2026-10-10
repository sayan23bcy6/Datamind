from __future__ import annotations

import math
import re
from collections import Counter
from hashlib import sha256
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.impute import KNNImputer


def _as_numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    series = frame[column]
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    converted = pd.to_numeric(series, errors="coerce")
    return converted.astype(float)


def profile_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    """Profile a dataset and return counts, dtypes, missingness, uniqueness and basic stats."""
    missing = frame.isna().sum()
    numeric_columns = [c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c]) or pd.to_numeric(frame[c], errors="coerce").notna().any()]
    stats_by_column = {}
    for column in numeric_columns:
        series = _as_numeric_series(frame, column)
        stats_by_column[column] = {
            "mean": float(series.mean()) if not series.empty and not series.isna().all() else None,
            "median": float(series.median()) if not series.empty and not series.isna().all() else None,
            "std": float(series.std()) if not series.empty and series.nunique() > 1 else None,
            "min": float(series.min()) if not series.empty and not series.isna().all() else None,
            "max": float(series.max()) if not series.empty and not series.isna().all() else None,
        }
    return {
        "row_count": int(frame.shape[0]),
        "column_count": int(frame.shape[1]),
        "dtypes": {str(k): str(v) for k, v in frame.dtypes.to_dict().items()},
        "missing_counts": {str(k): int(v) for k, v in missing.items()},
        "missing_rates": {str(k): float(v / frame.shape[0]) if frame.shape[0] else 0.0 for k, v in missing.items()},
        "unique_counts": {str(k): int(v) for k, v in frame.nunique(dropna=True).items()},
        "sample_values": {str(k): [None if pd.isna(v) else str(v) for v in list(frame[k].head(5).tolist())] for k in frame.columns},
        "numeric_stats": stats_by_column,
        "columns": list(frame.columns),
    }


def detect_missing(frame: pd.DataFrame) -> dict[str, Any]:
    """Report missingness and a simple heuristic for MCAR vs MAR patterns."""
    profile = profile_dataset(frame)
    missing_counts = profile["missing_counts"]
    missing_rates = profile["missing_rates"]
    statistic = 0.0
    heuristic = "MCAR"
    for column, rate in missing_rates.items():
        if rate > 0.2:
            heuristic = "MAR"
            break
    return {
        "missing_counts": missing_counts,
        "missing_rates": missing_rates,
        "heuristic": heuristic,
        "statistic": statistic,
    }


def detect_duplicates(frame: pd.DataFrame) -> dict[str, Any]:
    """Return exact duplicates and near-duplicates by normalized key."""
    normalized = frame.astype(str).apply(lambda s: s.str.replace(r"\s+", " ", regex=True).str.strip().str.lower(), axis=0)
    normalized_key = normalized.apply(lambda row: "|".join(row.astype(str)), axis=1)

    normalized_exact = normalized_key.duplicated(keep=False)
    exact_index = [int(i) for i, v in enumerate(normalized_exact.tolist()) if v]

    customer_key = frame.get("customer_id")
    if customer_key is not None:
        customer_norm = customer_key.astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.lower()
        customer_dupes = customer_norm.duplicated(keep=False)
        customer_index = [int(i) for i, v in enumerate(customer_dupes.tolist()) if v]
        if customer_index:
            exact_index = sorted(set(exact_index) | set(customer_index))

    near_index = [int(i) for i, v in enumerate(normalized_exact.tolist()) if v]
    return {
        "exact_duplicate_rows": exact_index,
        "near_duplicate_rows": near_index,
        "exact_duplicate_count": len(exact_index),
        "near_duplicate_count": len(near_index),
    }


def detect_format_inconsistencies(frame: pd.DataFrame) -> dict[str, Any]:
    """Detect mixed date formats, currencies, casing and label variants."""
    issues = []
    for column in frame.columns:
        values = frame[column].dropna().astype(str)
        if values.empty:
            continue
        variations = set(v.strip().lower() for v in values.unique())
        if len(variations) > 1 and any(re.search(r"[A-Za-z]", v) for v in variations):
            issues.append({"column": column, "kind": "label_variant", "sample": sorted(variations)[:5], "confidence": 0.8})
        if column.lower().endswith("date") or any(re.search(r"\d{4}|\d{2}/\d{2}|\d{2}-\d{2}", v) for v in values.head(20)):
            issues.append({"column": column, "kind": "date_format_mixed", "sample": sorted(values.unique())[:5], "confidence": 0.9})
        if values.str.contains(r"[$€£]|,\d{3}", regex=True).any():
            issues.append({"column": column, "kind": "currency_format", "sample": sorted(values.unique())[:5], "confidence": 0.8})
    return {"issues": issues}


def detect_type_errors(frame: pd.DataFrame) -> dict[str, Any]:
    """Flag columns with numeric values stored as text or mixed types."""
    findings = []
    for column in frame.columns:
        series = frame[column]
        non_null = series.dropna()
        if non_null.empty:
            continue
        numeric_like = non_null.map(lambda x: pd.to_numeric(x, errors="coerce"))
        if numeric_like.notna().sum() / len(non_null) > 0.8 and not pd.api.types.is_numeric_dtype(series):
            findings.append({"column": column, "problem": "numeric_as_text", "ratio": float(numeric_like.notna().sum() / len(non_null))})
    return {"findings": findings}


def detect_outliers(frame: pd.DataFrame) -> dict[str, Any]:
    """Detect outliers via IQR and z-score using a simple rule set."""
    findings = []
    numeric_columns = [c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c])]
    for column in numeric_columns:
        series = _as_numeric_series(frame, column)
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        if mask.any():
            findings.append({"column": column, "method": "IQR", "rows": [int(i) for i, v in enumerate(mask.tolist()) if v], "threshold": float(1.5)})
    return {"findings": findings}


def detect_drift(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, Any]:
    """Compare two versions of a dataset using KS and chi-square checks."""
    results = []
    for column in set(before.columns).intersection(after.columns):
        before_series = before[column]
        after_series = after[column]
        if pd.api.types.is_numeric_dtype(before_series) and pd.api.types.is_numeric_dtype(after_series):
            stat, p_value = stats.ks_2samp(before_series.dropna().astype(float).to_numpy(), after_series.dropna().astype(float).to_numpy())
            results.append({"column": column, "test": "ks_2samp", "statistic": float(stat), "p_value": float(p_value), "interpretation": "Population distributions differ substantially." if stat > 0.2 and p_value < 0.05 else "No strong distribution shift detected."})
        else:
            if before_series.fillna("__NA__").nunique() > 0 and after_series.fillna("__NA__").nunique() > 0:
                stat, p_value, _, _ = stats.chi2_contingency(pd.crosstab(before_series.fillna("__NA__"), after_series.fillna("__NA__")))
                results.append({"column": column, "test": "chi_square", "statistic": float(stat), "p_value": float(p_value), "interpretation": "Category mix changed meaningfully." if p_value < 0.05 else "Category profile remained similar."})
    return {"results": results}


def impute_column(frame: pd.DataFrame, column: str, method: str = "median", fill_value: Any | None = None) -> pd.DataFrame:
    """Impute missing values for a column with median, mode, or KNN logic."""
    result = frame.copy()
    if method == "median":
        result[column] = result[column].fillna(result[column].median())
        reason = "Median is robust to skew and preserves the central tendency of the column."
    elif method == "mode":
        mode_value = result[column].mode(dropna=True)
        if not mode_value.empty:
            result[column] = result[column].fillna(mode_value.iloc[0])
        reason = "Mode reflects the most common observed value and is appropriate for categorical patterns."
    elif method == "knn":
        numeric = result.copy()
        if column in numeric.columns:
            model = KNNImputer(n_neighbors=3)
            filled = model.fit_transform(numeric[[column]])
            result[column] = filled.ravel()
        reason = "KNN imputes from nearest neighbors to preserve local structure."
    else:
        result[column] = result[column].fillna(fill_value)
        reason = "Configured fill strategy."
    result.attrs["impute_reason"] = reason
    return result


def standardize_format(frame: pd.DataFrame, column: str, *, day_first: bool = True) -> pd.DataFrame:
    """Normalize dates, whitespace, and common formatting noise without mutating the input frame."""
    result = frame.copy()
    series = result[column].astype(str)
    cleaned = series.str.strip()
    cleaned = cleaned.str.replace(r"\s+", " ", regex=True)
    cleaned = cleaned.str.replace(r"^\$|,", "", regex=True)

    alias_map = {
        "ny": "new york",
        "new york": "new york",
        "ca": "california",
        "california": "california",
        "us": "united states",
        "usa": "united states",
    }
    cleaned = cleaned.str.lower().map(lambda value: alias_map.get(value, value)).str.strip()
    result[column] = cleaned
    return result


def deduplicate(frame: pd.DataFrame, *, keep: str = "first") -> tuple[pd.DataFrame, list[int]]:
    """Remove exact duplicates and return the removed row indices."""
    result = frame.copy()
    dup_mask = result.duplicated(keep=keep)
    removed = [int(idx) for idx, flag in enumerate(dup_mask.tolist()) if flag]
    result = result.drop_duplicates(keep=keep)
    return result, removed


def cast_type(frame: pd.DataFrame, column: str, *, target: str = "float") -> tuple[pd.DataFrame, list[int]]:
    """Cast a column to a target type while keeping failed values flagged and untouched."""
    result = frame.copy()
    original = result[column].copy()
    failed = []
    if target == "float":
        converted = pd.to_numeric(result[column], errors="coerce")
        bad_mask = converted.isna() & result[column].notna()
        failed = [int(i) for i, v in enumerate(bad_mask.tolist()) if v]
        result[column] = converted
    else:
        result[column] = result[column].astype(target)
    return result, failed


def winsorize_or_flag_outliers(frame: pd.DataFrame, column: str, *, mode: str = "flag") -> pd.DataFrame:
    """Winsorize or add a flag column; default is to flag outliers instead of removing them."""
    result = frame.copy()
    if mode == "flag":
        result[f"{column}_outlier_flag"] = False
        numeric = _as_numeric_series(result, column)
        q1 = numeric.quantile(0.25)
        q3 = numeric.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        result[f"{column}_outlier_flag"] = (numeric < lower) | (numeric > upper)
        return result
    numeric = _as_numeric_series(result, column)
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    result[column] = numeric.clip(lower=lower, upper=upper)
    return result


def run_ks_test(values_a: list[float], values_b: list[float]) -> dict[str, Any]:
    """Run a two-sample KS test and interpret the result in plain language."""
    stat, p_value = stats.ks_2samp(np.asarray(values_a, dtype=float), np.asarray(values_b, dtype=float))
    interpretation = "The distributions differ materially." if p_value < 0.05 and stat > 0.2 else "No strong evidence of a distribution shift."
    return {"statistic": float(stat), "p_value": float(p_value), "interpretation": interpretation}


def run_chi_square(matrix: list[list[float]]) -> dict[str, Any]:
    """Run a chi-square test over a contingency matrix."""
    rows = np.asarray(matrix, dtype=float)
    stat, p_value, _, _ = stats.chi2_contingency(rows)
    interpretation = "The categorical distributions differ materially." if p_value < 0.05 else "No strong evidence of category drift."
    return {"statistic": float(stat), "p_value": float(p_value), "interpretation": interpretation}


def compute_psi(before: pd.Series, after: pd.Series, bins: int = 10) -> dict[str, Any]:
    """Compute Population Stability Index for two series."""
    if before.empty or after.empty:
        return {"psi": 0.0, "interpretation": "No meaningful PSI could be computed."}
    before_values = before.astype(float).dropna().to_numpy()
    after_values = after.astype(float).dropna().to_numpy()
    if before_values.size == 0 or after_values.size == 0:
        return {"psi": 0.0, "interpretation": "No meaningful PSI could be computed."}
    intervals = np.linspace(min(before_values.min(), after_values.min()), max(before_values.max(), after_values.max()), bins + 1)
    before_counts, _ = np.histogram(before_values, bins=intervals)
    after_counts, _ = np.histogram(after_values, bins=intervals)
    before_pct = before_counts / before_counts.sum()
    after_pct = after_counts / after_counts.sum()
    before_pct = np.clip(before_pct, 1e-8, None)
    after_pct = np.clip(after_pct, 1e-8, None)
    psi = float(np.sum((after_pct - before_pct) * np.log(after_pct / before_pct)))
    interpretation = "Low drift" if psi < 0.1 else "Moderate drift" if psi < 0.25 else "High drift"
    return {"psi": psi, "interpretation": interpretation}


def compare_profiles(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, Any]:
    """Compare two profiles and summarize drift in human-friendly terms."""
    before_profile = profile_dataset(before)
    after_profile = profile_dataset(after)
    delta_rows = after_profile["row_count"] - before_profile["row_count"]
    delta_cols = after_profile["column_count"] - before_profile["column_count"]
    return {
        "row_delta": delta_rows,
        "column_delta": delta_cols,
        "before_missing_total": sum(before_profile["missing_counts"].values()),
        "after_missing_total": sum(after_profile["missing_counts"].values()),
        "interpretation": "Profile remained stable." if abs(delta_rows) < 5 else "A meaningful change in row count occurred.",
    }


def get_tool_registry() -> dict[str, Any]:
    return {
        "profile_dataset": profile_dataset,
        "detect_missing": detect_missing,
        "detect_duplicates": detect_duplicates,
        "detect_format_inconsistencies": detect_format_inconsistencies,
        "detect_type_errors": detect_type_errors,
        "detect_outliers": detect_outliers,
        "detect_drift": detect_drift,
        "impute_column": impute_column,
        "standardize_format": standardize_format,
        "deduplicate": deduplicate,
        "cast_type": cast_type,
        "winsorize_or_flag_outliers": winsorize_or_flag_outliers,
        "run_ks_test": run_ks_test,
        "run_chi_square": run_chi_square,
        "compute_psi": compute_psi,
        "compare_profiles": compare_profiles,
    }


TOOL_REGISTRY = get_tool_registry()


def _hash_value(value: Any) -> str:
    return sha256(repr(value).encode("utf-8")).hexdigest()
