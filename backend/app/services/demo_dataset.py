from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def generate_demo_dataset(output_dir: str | Path | None = None, name: str = "demo_customer_data.csv") -> dict[str, Any]:
    """Generates customer and transaction data with carefully planted data quality issues.
    Writes both the CSV dataset and a sidecar JSON documenting all planted issues.
    """
    output_path = Path(output_dir) if output_dir is not None else Path("./storage/demo")
    output_path.mkdir(parents=True, exist_ok=True)

    # 25 rows designed deterministically with all planted issues
    records = [
        # Customer 1 - Standard
        {"customer_id": "C-101", "name": "Alice Smith", "signup_date": "2024/01/15", "transaction_id": "TX-9001", "transaction_date": "2024-01-20", "transaction_amount": "$150.00", "state": "New York", "account_type": "Premium", "credit_score": "740", "account_status": "active", "notes": "Onboarded via web"},
        # Customer 2 - Standard
        {"customer_id": "C-102", "name": "Bob Jones", "signup_date": "02-18-2024", "transaction_id": "TX-9002", "transaction_date": "2024-02-20", "transaction_amount": "$220.50", "state": "CA", "account_type": "Standard", "credit_score": "680", "account_status": "active", "notes": "Referred by branch"},
        # Exact duplicate of row 1 (Customer 1)
        {"customer_id": "C-101", "name": "Alice Smith", "signup_date": "2024/01/15", "transaction_id": "TX-9001", "transaction_date": "2024-01-20", "transaction_amount": "$150.00", "state": "New York", "account_type": "Premium", "credit_score": "740", "account_status": "active", "notes": "Onboarded via web"},
        # Customer 3 - Near duplicate of Bob Jones with casing & trailing spaces
        {"customer_id": "c-102 ", "name": "bob jones ", "signup_date": "2024-02-18", "transaction_id": "tx-9002", "transaction_date": "2024-02-20", "transaction_amount": "220.50", "state": "ca ", "account_type": "Standard", "credit_score": "680", "account_status": "active", "notes": "referred by branch"},
        # Customer 4 - Planted outlier 1: transaction_amount = $99,999.00
        {"customer_id": "C-104", "name": "Diana Vance", "signup_date": "03/10/2024", "transaction_id": "TX-9004", "transaction_date": "2024-03-12", "transaction_amount": "$99,999.00", "state": "NY", "account_type": "Enterprise", "credit_score": "810", "account_status": "active", "notes": "High volume trader"},
        # Customer 5 - Standard with label variant "new york "
        {"customer_id": "C-105", "name": "Evan Wright", "signup_date": "2024-03-22", "transaction_id": "TX-9005", "transaction_date": "2024-03-25", "transaction_amount": "$310.00", "state": "new york ", "account_type": "Standard", "credit_score": "710", "account_status": "active", "notes": "Normal activity"},
        # Customer 6 - Planted outlier 2: transaction_amount = $125,000.50
        {"customer_id": "C-106", "name": "Fiona Gallagher", "signup_date": "2024/04/05", "transaction_id": "TX-9006", "transaction_date": "2024-04-10", "transaction_amount": "$125,000.50", "state": "California", "account_type": "Enterprise", "credit_score": "790", "account_status": "active", "notes": "Commercial real estate"},
        # Customer 7 - Missingness depends on account_status: closed account has missing notes and credit_score
        {"customer_id": "C-107", "name": "George Clark", "signup_date": "04-18-2024", "transaction_id": "TX-9007", "transaction_date": "2024-04-20", "transaction_amount": "$85.00", "state": "TX", "account_type": "Basic", "credit_score": "", "account_status": "closed", "notes": ""},
        # Exact duplicate of row 5 (Evan Wright)
        {"customer_id": "C-105", "name": "Evan Wright", "signup_date": "2024-03-22", "transaction_id": "TX-9005", "transaction_date": "2024-03-25", "transaction_amount": "$310.00", "state": "new york ", "account_type": "Standard", "credit_score": "710", "account_status": "active", "notes": "Normal activity"},
        # Customer 8 - Planted outlier 3: transaction_amount = $88,888.00
        {"customer_id": "C-108", "name": "Hannah Abbott", "signup_date": "05/12/2024", "transaction_id": "TX-9008", "transaction_date": "2024-05-15", "transaction_amount": "$88,888.00", "state": "Texas", "account_type": "Enterprise", "credit_score": "760", "account_status": "active", "notes": "Capital expenditure"},
        # Customer 9 - Closed account missing credit_score & notes (MAR)
        {"customer_id": "C-109", "name": "Ian Malcolm", "signup_date": "2024-05-30", "transaction_id": "TX-9009", "transaction_date": "2024-06-01", "transaction_amount": "$45.00", "state": "NY", "account_type": "Basic", "credit_score": "", "account_status": "closed", "notes": ""},
        # Customer 10 - Standard
        {"customer_id": "C-110", "name": "Julia Roberts", "signup_date": "2024/06/14", "transaction_id": "TX-9010", "transaction_date": "2024-06-18", "transaction_amount": "$195.00", "state": "California", "account_type": "Standard", "credit_score": "725", "account_status": "active", "notes": "Mobile app signup"},
        # Customer 11 - Standard with thousands separator
        {"customer_id": "C-111", "name": "Kevin Bacon", "signup_date": "06-25-2024", "transaction_id": "TX-9011", "transaction_date": "2024-06-28", "transaction_amount": "$1,450.00", "state": "TX", "account_type": "Premium", "credit_score": "695", "account_status": "active", "notes": "Preferred tier"},
        # Customer 12 - Number stored as text with "N/A"
        {"customer_id": "C-112", "name": "Laura Croft", "signup_date": "2024-07-04", "transaction_id": "TX-9012", "transaction_date": "2024-07-08", "transaction_amount": "$380.00", "state": "New York", "account_type": "Standard", "credit_score": "N/A", "account_status": "active", "notes": "Pending credit check"},
        # Customer 13 - Standard
        {"customer_id": "C-113", "name": "Michael Scott", "signup_date": "07/19/2024", "transaction_id": "TX-9013", "transaction_date": "2024-07-22", "transaction_amount": "$520.00", "state": "NY", "account_type": "Standard", "credit_score": "640", "account_status": "active", "notes": "Regional manager"},
        # Customer 14 - Closed account missing credit_score & notes
        {"customer_id": "C-114", "name": "Nancy Wheeler", "signup_date": "2024/08/02", "transaction_id": "TX-9014", "transaction_date": "2024-08-05", "transaction_amount": "$60.00", "state": "CA", "account_type": "Basic", "credit_score": "", "account_status": "closed", "notes": ""},
        # Customer 15 - Standard
        {"customer_id": "C-115", "name": "Oscar Martinez", "signup_date": "08-15-2024", "transaction_id": "TX-9015", "transaction_date": "2024-08-18", "transaction_amount": "$275.00", "state": "Texas", "account_type": "Standard", "credit_score": "750", "account_status": "active", "notes": "Accounting lead"},
        # Customer 16 - Near duplicate of Michael Scott
        {"customer_id": "c-113", "name": "michael scott", "signup_date": "2024-07-19", "transaction_id": "tx-9013", "transaction_date": "2024-07-22", "transaction_amount": "520.00", "state": "ny", "account_type": "Standard", "credit_score": "640", "account_status": "active", "notes": "regional manager"},
        # Customer 17 - Standard
        {"customer_id": "C-117", "name": "Pam Beesly", "signup_date": "2024-09-01", "transaction_id": "TX-9017", "transaction_date": "2024-09-04", "transaction_amount": "$180.00", "state": "CA", "account_type": "Standard", "credit_score": "715", "account_status": "active", "notes": "Office administrator"},
        # Customer 18 - Standard
        {"customer_id": "C-118", "name": "Quentin Coldwater", "signup_date": "09/14/2024", "transaction_id": "TX-9018", "transaction_date": "2024-09-17", "transaction_amount": "$410.00", "state": "New York", "account_type": "Premium", "credit_score": "730", "account_status": "active", "notes": "Graduate subscriber"},
    ]

    df = pd.DataFrame(records)
    csv_file = output_path / name
    df.to_csv(csv_file, index=False)

    sidecar_data = {
        "dataset_name": "Demo Customer & Transactions Dataset",
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "planted_issues": {
            "date_formats_mixed": {
                "column": "signup_date",
                "formats": ["YYYY/MM/DD (e.g. 2024/01/15)", "MM-DD-YYYY (e.g. 02-18-2024)", "YYYY-MM-DD (e.g. 2024-03-22)", "MM/DD/YYYY (e.g. 03/10/2024)"],
                "count": 4,
            },
            "exact_duplicates": {
                "rows": [2, 8],
                "description": "Row 2 duplicates row 0 (Alice Smith); row 8 duplicates row 5 (Evan Wright)",
            },
            "near_duplicates": {
                "rows": [3, 17],
                "description": "Row 3 is near-duplicate of row 1 (Bob Jones); row 17 is near-duplicate of row 14 (Michael Scott)",
            },
            "currency_and_separators": {
                "column": "transaction_amount",
                "patterns": ["$ symbol prefix", "thousands comma separator (e.g. $1,450.00, $99,999.00)"],
            },
            "numbers_stored_as_text": {
                "columns": ["credit_score", "transaction_amount"],
                "description": "credit_score contains numbers, empty strings, and 'N/A'; transaction_amount contains currency text",
            },
            "dependent_missingness_mar": {
                "trigger_column": "account_status",
                "trigger_value": "closed",
                "affected_columns": ["notes", "credit_score"],
                "description": "When account_status is 'closed', notes and credit_score are missing",
            },
            "known_outliers": [
                {"column": "transaction_amount", "row_index": 4, "value": 99999.00, "customer": "Diana Vance"},
                {"column": "transaction_amount", "row_index": 6, "value": 125000.50, "customer": "Fiona Gallagher"},
                {"column": "transaction_amount", "row_index": 9, "value": 88888.00, "customer": "Hannah Abbott"},
            ],
            "label_variants": {
                "column": "state",
                "variants": ["NY", "New York", "new york ", "CA", "California", "ca ", "TX", "Texas"],
                "canonical_target": {"NY": "New York", "CA": "California", "TX": "Texas"},
            },
        },
    }

    sidecar_file = output_path / f"{Path(name).stem}.json"
    sidecar_file.write_text(json.dumps(sidecar_data, indent=2), encoding="utf-8")

    return {
        "path": str(csv_file),
        "sidecar_path": str(sidecar_file),
        "rows": len(df),
        "columns": len(df.columns),
        "planted_issues": sidecar_data["planted_issues"],
        "problem_columns": ["country", "state", "signup_date", "transaction_amount", "credit_score", "notes"],
    }
