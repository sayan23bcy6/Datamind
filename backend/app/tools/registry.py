from app.tools.detectors import (
    calculate_dimension_scores,
    cast_type,
    compute_column_distributions,
    compute_psi,
    deduplicate,
    detect_drift,
    detect_duplicates,
    detect_format_inconsistencies,
    detect_missing,
    detect_outliers,
    detect_type_errors,
    impute_column,
    profile_dataset,
    standardize_format,
    winsorize_or_flag_outliers,
)

TOOL_REGISTRY = {
    "profile_dataset": profile_dataset,
    "calculate_dimension_scores": calculate_dimension_scores,
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
    "compute_psi": compute_psi,
    "compute_column_distributions": compute_column_distributions,
}

__all__ = ["TOOL_REGISTRY"]
