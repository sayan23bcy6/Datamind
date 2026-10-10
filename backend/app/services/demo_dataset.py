from __future__ import annotations

from pathlib import Path

import pandas as pd


def generate_demo_dataset(output_dir: str | Path | None = None, name: str = "demo_customer_data.csv") -> dict:
    output_path = Path(output_dir) if output_dir is not None else Path("./storage/demo")
    output_path.mkdir(parents=True, exist_ok=True)

    data = {
        "customer_id": ["C-001", "C-002", "C-003", "C-004", "C-005", "C-006", "C-007", "C-008", "C-009", "C-010", "C-011", "C-012", "C-013", "C-014", "C-015"],
        "signup_date": ["2024/01/05", "04-16-2024", "2024-02-28", "2024/03/07", "04/10/2024", "2024-05-22", "2024-06-13", "2024/12/01", "", "2024-07-09", "2024-08-19", "2024-09-21", "2024-10-07", "2024-11-01", "2024-12-11"],
        "country": ["NY", "New York", "new york", "CA", "California", "TX", "Texas", "NY", "Florida", "FL", "new york", "NY", "California", "CA", "Texas"],
        "phone": ["(212) 555-0111", "2125550122", "212-555-0133", "415-555-0144", "4155550145", "6155550156", "615-555-0187", "2125550111", "3055550199", "305-555-0200", "2125550211", "", "4155550222", "415-555-0223", "615-555-0244"],
        "annual_revenue": ["$120000.00", "$98000.50", "$95,000.00", "$175000", "$99999.99", "$115000", "$96000", "N/A", "$212500.00", "$130000", "$135000.00", "$89000", "$200000.00", "$215000", "$87900"],
        "segment": ["Enterprise", "SMB", "Enterprise", "SMB", "Enterprise", "SMB", "SMB", "Enterprise", "Enterprise", "SMB", "Enterprise", "SMB", "SMB", "Enterprise", "SMB"],
        "email": ["alice@acme.com", "bob@example.com", "carol@acme.com", "dan@northstar.io", "erin@example.com", "frank@northstar.io", "grace@demo.net", "alice@acme.com", "hannah@example.com", "ivan@acme.com", "jenny@northstar.io", "kevin@example.com", "laura@demo.net", "marc@example.com", "nina@acme.com"],
        "notes": ["OK", "dup", "OK", "OK", "OK", "OK", "OK", "dup", "OK", "OK", "OK", "missing", "OK", "OK", "OK"],
    }

    df = pd.DataFrame(data)
    file_path = output_path / name
    df.to_csv(file_path, index=False)

    return {
        "path": str(file_path),
        "rows": len(df),
        "columns": len(df.columns),
        "problem_columns": ["signup_date", "country", "phone", "annual_revenue"],
    }
