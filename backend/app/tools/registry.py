from app.tools.detectors import (
    cast_type,
    compare_profiles,
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
    run_chi_square,
    run_ks_test,
    standardize_format,
    winsorize_or_flag_outliers,
)

TOOL_REGISTRY = {
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

__all__ = ["TOOL_REGISTRY"]
