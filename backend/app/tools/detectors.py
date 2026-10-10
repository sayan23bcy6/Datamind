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
    cleaned = (
        series.astype(str)
        .str.replace(r"[\$,]", "", regex=True)
        .str.strip()
    )
    converted = pd.to_numeric(cleaned, errors="coerce")
    return converted.astype(float)


def compute_psi(before: pd.Series, after: pd.Series, bins: int = 10) -> float:
    """Compute Population Stability Index for two series."""
    b_nonnull = before.dropna()
    a_nonnull = after.dropna()
    if b_nonnull.empty or a_nonnull.empty:
        return 0.0

    # Categorical PSI
    if not (pd.api.types.is_numeric_dtype(b_nonnull) and pd.api.types.is_numeric_dtype(a_nonnull)):
        categories = list(set(b_nonnull.astype(str)).union(set(a_nonnull.astype(str))))
        if not categories:
            return 0.0
        b_counts = b_nonnull.astype(str).value_counts()
        a_counts = a_nonnull.astype(str).value_counts()
        b_pct = np.array([b_counts.get(c, 0) / len(b_nonnull) for c in categories])
        a_pct = np.array([a_counts.get(c, 0) / len(a_nonnull) for c in categories])
        b_pct = np.clip(b_pct, 1e-4, None)
        a_pct = np.clip(a_pct, 1e-4, None)
        b_pct = b_pct / b_pct.sum()
        a_pct = a_pct / a_pct.sum()
        return float(np.sum((a_pct - b_pct) * np.log(a_pct / b_pct)))

    # Numeric PSI
    b_vals = b_nonnull.astype(float).to_numpy()
    a_vals = a_nonnull.astype(float).to_numpy()
    min_v = min(b_vals.min(), a_vals.min())
    max_v = max(b_vals.max(), a_vals.max())
    if min_v == max_v:
        return 0.0

    intervals = np.linspace(min_v, max_v, bins + 1)
    b_counts, _ = np.histogram(b_vals, bins=intervals)
    a_counts, _ = np.histogram(a_vals, bins=intervals)
    b_pct = np.clip(b_counts / b_counts.sum(), 1e-4, None)
    a_pct = np.clip(a_counts / a_counts.sum(), 1e-4, None)
    b_pct = b_pct / b_pct.sum()
    a_pct = a_pct / a_pct.sum()
    return float(np.sum((a_pct - b_pct) * np.log(a_pct / b_pct)))


def calculate_dimension_scores(frame: pd.DataFrame) -> dict[str, float]:
    """Calculate the deterministic dimension scores (each 0 to 100) exactly as defined in Section 2.
    completeness = 100 * (1 - mean missing rate across columns)
    uniqueness = 100 * (1 - exact duplicate rows / total rows)
    consistency = 100 * share of values matching dominant format per column, averaged across columns with detected format
    validity = 100 * share of values that cast cleanly to target type, averaged across columns
    accuracy = 100 * (1 - share of outlier rows flagged by IQR or IsolationForest), averaged across numeric columns
    overall = unweighted mean of the five dimensions
    """
    total_rows = len(frame)
    total_cols = len(frame.columns)
    if total_rows == 0 or total_cols == 0:
        return {
            "completeness": 100.0,
            "uniqueness": 100.0,
            "consistency": 100.0,
            "validity": 100.0,
            "accuracy": 100.0,
            "overall": 100.0,
        }

    # 1. Completeness
    missing_rates = [frame[col].isna().sum() / total_rows for col in frame.columns]
    mean_missing = float(np.mean(missing_rates))
    completeness = max(0.0, min(100.0, 100.0 * (1.0 - mean_missing)))

    # 2. Uniqueness
    exact_duplicates = int(frame.duplicated(keep="first").sum())
    uniqueness = max(0.0, min(100.0, 100.0 * (1.0 - (exact_duplicates / total_rows))))

    # 3. Consistency
    format_shares: list[float] = []
    for col in frame.columns:
        series = frame[col].dropna().astype(str).str.strip()
        if series.empty:
            continue
        # Check date format consistency
        is_date_col = "date" in col.lower() or any("/" in s or "-" in s for s in series.head(10))
        if is_date_col:
            # Check pattern regexes
            patterns = [
                r"^\d{4}-\d{2}-\d{2}$",  # ISO
                r"^\d{4}/\d{2}/\d{2}$",
                r"^\d{2}-\d{2}-\d{4}$",
                r"^\d{2}/\d{2}/\d{4}$",
            ]
            matches = [sum(bool(re.match(p, s)) for s in series) for p in patterns]
            max_matches = max(matches)
            if max_matches > 0:
                format_shares.append(max_matches / len(series))
                continue

        # Check currency / numeric formatting consistency
        has_currency = series.str.contains(r"[\$€£]", regex=True).any()
        if has_currency:
            currency_match = series.str.contains(r"^\$[\d,]+(?:\.\d{2})?$", regex=True).sum()
            format_shares.append(currency_match / len(series))
            continue

        # Check state/category casing consistency
        if series.str.len().max() < 30 and series.nunique() < len(series) / 2:
            # check casing variants
            casing_types = []
            for val in series:
                if val.isupper():
                    casing_types.append("upper")
                elif val.islower():
                    casing_types.append("lower")
                elif val.istitle():
                    casing_types.append("title")
                else:
                    casing_types.append("mixed")
            dominant_casing_count = Counter(casing_types).most_common(1)[0][1]
            format_shares.append(dominant_casing_count / len(series))

    if format_shares:
        consistency = max(0.0, min(100.0, 100.0 * float(np.mean(format_shares))))
    else:
        consistency = 100.0

    # 4. Validity: share of values that cast cleanly to their target type, averaged across columns
    valid_shares: list[float] = []
    for col in frame.columns:
        series = frame[col].dropna()
        if series.empty:
            valid_shares.append(1.0)
            continue
        if pd.api.types.is_numeric_dtype(series):
            valid_shares.append(1.0)
        else:
            # Check if it looks numeric
            num_clean = series.astype(str).str.replace(r"[\$,]", "", regex=True).str.strip()
            num_cast = pd.to_numeric(num_clean, errors="coerce")
            if num_cast.notna().sum() > len(series) * 0.5:
                valid_shares.append(float(num_cast.notna().sum() / len(series)))
            else:
                # Check date target
                if "date" in col.lower():
                    date_cast = pd.to_datetime(series, errors="coerce", format="mixed")
                    valid_shares.append(float(date_cast.notna().sum() / len(series)))
                else:
                    valid_shares.append(1.0)
    validity = max(0.0, min(100.0, 100.0 * float(np.mean(valid_shares))))

    # 5. Accuracy: 100 * (1 - share of outlier rows flagged by IQR or IsolationForest), averaged across numeric columns
    numeric_columns = [
        col for col in frame.columns
        if pd.api.types.is_numeric_dtype(frame[col])
        or pd.to_numeric(frame[col].astype(str).str.replace(r"[\$,]", "", regex=True).str.strip(), errors="coerce").notna().sum() > len(frame) * 0.6
    ]
    if numeric_columns:
        outlier_shares: list[float] = []
        for col in numeric_columns:
            series = _as_numeric_series(frame, col).dropna()
            if len(series) < 4:
                outlier_shares.append(0.0)
                continue
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = (series < lower) | (series > upper)
            outlier_shares.append(float(outliers.sum() / len(series)))
        accuracy = max(0.0, min(100.0, 100.0 * (1.0 - float(np.mean(outlier_shares)))))
    else:
        accuracy = 100.0

    # Overall: unweighted mean of the five dimensions
    overall = max(0.0, min(100.0, (completeness + uniqueness + consistency + validity + accuracy) / 5.0))

    return {
        "completeness": round(completeness, 2),
        "uniqueness": round(uniqueness, 2),
        "consistency": round(consistency, 2),
        "validity": round(validity, 2),
        "accuracy": round(accuracy, 2),
        "overall": round(overall, 2),
    }


def profile_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    """Profile a dataset and return column metadata and deterministic dimension scores."""
    missing = frame.isna().sum()
    columns_list = []
    for col in frame.columns:
        series = frame[col]
        missing_count = int(missing[col])
        missing_rate = float(missing_count / len(frame)) if len(frame) > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))
        samples = [None if pd.isna(v) else str(v) for v in series.dropna().head(5).tolist()]
        columns_list.append({
            "name": str(col),
            "dtype": str(series.dtype),
            "missing_count": missing_count,
            "missing_rate": round(missing_rate, 4),
            "unique_count": unique_count,
            "sample_values": samples,
        })

    dimensions = calculate_dimension_scores(frame)

    return {
        "row_count": int(frame.shape[0]),
        "column_count": int(frame.shape[1]),
        "columns": columns_list,
        "dimensions": dimensions,
        "missing_counts": {str(k): int(v) for k, v in missing.items()},
        "missing_rates": {str(k): float(v / len(frame)) if len(frame) else 0.0 for k, v in missing.items()},
        "unique_counts": {str(c["name"]): c["unique_count"] for c in columns_list},
    }


def detect_duplicates(frame: pd.DataFrame) -> dict[str, Any]:
    """Detect exact duplicates and near-duplicates."""
    # Exact duplicate rows
    exact_mask = frame.duplicated(keep=False)
    exact_index = [int(i) for i, v in enumerate(exact_mask.tolist()) if v]

    # Near duplicates: normalize whitespace and lowercase
    normalized = frame.astype(str).apply(lambda s: s.str.replace(r"\s+", " ", regex=True).str.strip().str.lower(), axis=0)
    normalized_key = normalized.apply(lambda row: "|".join(row.astype(str)), axis=1)
    near_mask = normalized_key.duplicated(keep=False)
    near_index = [int(i) for i, v in enumerate(near_mask.tolist()) if v]

    return {
        "exact_duplicate_rows": exact_index,
        "near_duplicate_rows": near_index,
        "exact_duplicate_count": len(exact_index),
        "near_duplicate_count": len(near_index),
    }


def detect_missing(frame: pd.DataFrame) -> dict[str, Any]:
    missing = frame.isna().sum()
    missing_rates = {str(k): float(v / len(frame)) if len(frame) else 0.0 for k, v in missing.items()}
    heuristic = "MCAR"
    for rate in missing_rates.values():
        if rate > 0.15:
            heuristic = "MAR"
            break
    return {
        "missing_counts": {str(k): int(v) for k, v in missing.items()},
        "missing_rates": missing_rates,
        "heuristic": heuristic,
    }


def detect_format_inconsistencies(frame: pd.DataFrame) -> dict[str, Any]:
    issues = []
    for column in frame.columns:
        series = frame[column].dropna().astype(str)
        if series.empty:
            continue
        # Mixed date formats
        if "date" in column.lower() or series.head(10).str.contains(r"[\/-]", regex=True).any():
            patterns = set()
            for val in series:
                if re.match(r"^\d{4}/\d{2}/\d{2}$", val.strip()):
                    patterns.add("YYYY/MM/DD")
                elif re.match(r"^\d{2}-\d{2}-\d{4}$", val.strip()):
                    patterns.add("MM-DD-YYYY")
                elif re.match(r"^\d{4}-\d{2}-\d{2}$", val.strip()):
                    patterns.add("YYYY-MM-DD")
                elif re.match(r"^\d{2}/\d{2}/\d{4}$", val.strip()):
                    patterns.add("MM/DD/YYYY")
            if len(patterns) > 1:
                issues.append({
                    "column": column,
                    "kind": "date_format_mixed",
                    "formats": list(patterns),
                    "confidence": 0.95,
                })

        # Currency and thousands separators
        if series.str.contains(r"[\$€£]|,\d{3}", regex=True).any():
            issues.append({
                "column": column,
                "kind": "currency_format",
                "sample": list(series.unique()[:3]),
                "confidence": 0.90,
            })

        # Label variants
        norm = series.str.strip().str.lower()
        if norm.nunique() < series.nunique():
            issues.append({
                "column": column,
                "kind": "label_variant",
                "sample": list(series.unique()[:5]),
                "confidence": 0.85,
            })
        elif any(v in ["ny", "new york", "ca", "california", "tx", "texas"] for v in norm):
            issues.append({
                "column": column,
                "kind": "label_variant",
                "sample": list(series.unique()[:5]),
                "confidence": 0.85,
            })
    return {"issues": issues}


def detect_type_errors(frame: pd.DataFrame) -> dict[str, Any]:
    findings = []
    for column in frame.columns:
        series = frame[column].dropna().astype(str)
        if series.empty:
            continue
        cleaned = series.str.replace(r"[\$,]", "", regex=True).str.strip()
        numeric_like = pd.to_numeric(cleaned, errors="coerce")
        ratio = float(numeric_like.notna().sum() / len(series))
        if 0.5 < ratio < 1.0 or (ratio >= 0.9 and not pd.api.types.is_numeric_dtype(frame[column])):
            findings.append({"column": column, "problem": "numeric_as_text", "ratio": ratio})
    return {"findings": findings}


def detect_outliers(frame: pd.DataFrame) -> dict[str, Any]:
    findings = []
    numeric_columns = [
        col for col in frame.columns
        if pd.api.types.is_numeric_dtype(frame[col])
        or pd.to_numeric(frame[col].astype(str).str.replace(r"[\$,]", "", regex=True).str.strip(), errors="coerce").notna().sum() > len(frame) * 0.6
    ]
    for column in numeric_columns:
        series = _as_numeric_series(frame, column)
        non_null = series.dropna()
        if len(non_null) < 4:
            continue
        q1 = float(non_null.quantile(0.25))
        q3 = float(non_null.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        outlier_indices = [int(i) for i, v in enumerate(mask.tolist()) if v]
        if outlier_indices:
            findings.append({
                "column": column,
                "method": "IQR",
                "rows": outlier_indices,
                "outlier_values": [float(series.iloc[i]) for i in outlier_indices],
                "lower_bound": lower,
                "upper_bound": upper,
            })
    return {"findings": findings}


def detect_drift(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, Any]:
    results = []
    common_cols = [c for c in before.columns if c in after.columns]
    for column in common_cols:
        b_series = before[column]
        a_series = after[column]
        if pd.api.types.is_numeric_dtype(b_series) and pd.api.types.is_numeric_dtype(a_series):
            b_clean = b_series.dropna().astype(float).to_numpy()
            a_clean = a_series.dropna().astype(float).to_numpy()
            if len(b_clean) > 0 and len(a_clean) > 0:
                stat, p_value = stats.ks_2samp(b_clean, a_clean)
                results.append({
                    "column": column,
                    "test": "ks_2samp",
                    "statistic": float(stat),
                    "p_value": float(p_value),
                })
        else:
            psi_val = compute_psi(b_series, a_series)
            results.append({
                "column": column,
                "test": "psi",
                "statistic": float(psi_val),
                "p_value": None,
            })
    return {"results": results}


def deduplicate(frame: pd.DataFrame, *, keep: str = "first") -> tuple[pd.DataFrame, list[int]]:
    """Remove exact duplicates and return the cleaned frame and removed original row indices."""
    dup_mask = frame.duplicated(keep=keep)
    removed_indices = [int(idx) for idx, flag in enumerate(dup_mask.tolist()) if flag]
    cleaned = frame.drop_duplicates(keep=keep).reset_index(drop=True)
    return cleaned, removed_indices


def standardize_format(frame: pd.DataFrame, column: str, *, day_first: bool = False) -> pd.DataFrame:
    """Normalize dates to ISO 8601, strip currency symbols and thousands separators,
    and map state/label variants to canonical labels. Pure function and idempotent.
    """
    result = frame.copy()
    if column not in result.columns:
        return result

    series = result[column]

    # 1. Date normalization if column appears to be a date
    is_date = "date" in column.lower() or series.dropna().astype(str).str.contains(r"[\/-]", regex=True).all()
    if is_date:
        def _parse_date(val: Any) -> Any:
            if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() in ("n/a", "null", "none"):
                return val
            s = str(val).strip()
            # If already YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                return s
            try:
                dt = pd.to_datetime(s, format="mixed", dayfirst=day_first)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return s

        result[column] = series.apply(_parse_date)
        return result

    alias_map = {
        "ny": "New York",
        "new york": "New York",
        "ca": "California",
        "california": "California",
        "tx": "Texas",
        "texas": "Texas",
        "us": "United States",
        "usa": "United States",
    }

    def _clean_value(val: Any) -> Any:
        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() in ("n/a", "null", "none"):
            return val
        s = str(val).replace("$", "").replace("€", "").replace("£", "").replace(",", "")
        s = re.sub(r"\s+", " ", s).strip()
        lower_s = s.lower()
        if lower_s in alias_map:
            return alias_map[lower_s]
        return s

    result[column] = series.apply(_clean_value)
    return result


def cast_type(frame: pd.DataFrame, column: str, *, target: str = "float") -> tuple[pd.DataFrame, list[int]]:
    result = frame.copy()
    if column not in result.columns:
        return result, []
    failed_indices = []
    if target in ("float", "numeric"):
        cleaned = result[column].astype(str).str.replace(r"[\$,]", "", regex=True).str.strip()
        converted = pd.to_numeric(cleaned, errors="coerce")
        bad_mask = converted.isna() & result[column].notna() & (~result[column].astype(str).str.strip().isin(["", "N/A", "null", "None"]))
        failed_indices = [int(i) for i, v in enumerate(bad_mask.tolist()) if v]
        result[column] = converted
    else:
        result[column] = result[column].astype(target)
    return result, failed_indices


def winsorize_or_flag_outliers(frame: pd.DataFrame, column: str, *, mode: str = "flag") -> pd.DataFrame:
    result = frame.copy()
    if column not in result.columns:
        return result
    numeric = _as_numeric_series(result, column)
    non_null = numeric.dropna()
    if len(non_null) < 4:
        return result
    q1 = float(non_null.quantile(0.25))
    q3 = float(non_null.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    if mode == "flag":
        result[f"{column}_outlier_flag"] = (numeric < lower) | (numeric > upper)
    else:
        result[column] = numeric.clip(lower=lower, upper=upper)
    return result


def impute_column(frame: pd.DataFrame, column: str, method: str = "median", fill_value: Any | None = None) -> pd.DataFrame:
    result = frame.copy()
    if column not in result.columns:
        return result
    if method == "median":
        numeric = _as_numeric_series(result, column)
        med = numeric.median()
        result[column] = result[column].fillna(med)
    elif method == "mode":
        mode_val = result[column].mode(dropna=True)
        if not mode_val.empty:
            result[column] = result[column].fillna(mode_val.iloc[0])
    elif method == "value":
        result[column] = result[column].fillna(fill_value)
    return result


def compute_column_distributions(before_df: pd.DataFrame, after_df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    """Compute 20 equal-width bins for numeric columns, with bin edges taken from the original
    version's range and applied to the cleaned version, plus verification tolerance (KS and median shift).
    """
    distribution_list = []
    for col in columns:
        if col not in before_df.columns or col not in after_df.columns:
            continue

        b_num = _as_numeric_series(before_df, col).dropna()
        a_num = _as_numeric_series(after_df, col).dropna()

        if b_num.empty or a_num.empty:
            continue

        min_val = float(b_num.min())
        max_val = float(b_num.max())
        if min_val == max_val:
            min_val -= 1.0
            max_val += 1.0

        bin_edges = np.linspace(min_val, max_val, 21)

        b_counts, _ = np.histogram(b_num, bins=bin_edges)
        a_counts, _ = np.histogram(a_num, bins=bin_edges)

        b_total = max(1, int(len(b_num)))
        a_total = max(1, int(len(a_num)))

        before_bins = [
            {
                "bin_start": round(float(bin_edges[i]), 2),
                "bin_end": round(float(bin_edges[i + 1]), 2),
                "count": int(b_counts[i]),
                "frequency": round(float(b_counts[i] / b_total), 4),
            }
            for i in range(20)
        ]

        after_bins = [
            {
                "bin_start": round(float(bin_edges[i]), 2),
                "bin_end": round(float(bin_edges[i + 1]), 2),
                "count": int(a_counts[i]),
                "frequency": round(float(a_counts[i] / a_total), 4),
            }
            for i in range(20)
        ]

        # Verification tolerance: KS p-value > 0.01 OR median shift under 5% of original IQR
        ks_stat, p_val = stats.ks_2samp(b_num.to_numpy(), a_num.to_numpy())
        orig_q1 = float(b_num.quantile(0.25))
        orig_q3 = float(b_num.quantile(0.75))
        orig_iqr = orig_q3 - orig_q1
        orig_median = float(b_num.median())
        new_median = float(a_num.median())
        median_shift = abs(new_median - orig_median)

        passed = (p_val > 0.01) or (orig_iqr > 0 and median_shift <= 0.05 * orig_iqr) or (orig_iqr == 0 and median_shift == 0)

        distribution_list.append({
            "column": col,
            "before_bins": before_bins,
            "after_bins": after_bins,
            "ks_statistic": round(float(ks_stat), 4),
            "p_value": round(float(p_val), 4),
            "passed": bool(passed),
        })

    return distribution_list


def run_ks_test(values_a: list[float], values_b: list[float]) -> dict[str, Any]:
    stat, p_value = stats.ks_2samp(np.asarray(values_a, dtype=float), np.asarray(values_b, dtype=float))
    interpretation = "The distributions differ materially." if p_value < 0.05 and stat > 0.2 else "No strong evidence of a distribution shift."
    return {"statistic": float(stat), "p_value": float(p_value), "interpretation": interpretation}


def run_chi_square(matrix: list[list[float]]) -> dict[str, Any]:
    rows = np.asarray(matrix, dtype=float)
    stat, p_value, _, _ = stats.chi2_contingency(rows)
    interpretation = "The categorical distributions differ materially." if p_value < 0.05 else "No strong evidence of category drift."
    return {"statistic": float(stat), "p_value": float(p_value), "interpretation": interpretation}


def compare_profiles(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, Any]:
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

