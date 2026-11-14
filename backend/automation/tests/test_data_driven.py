"""Data-driven login test: ONE test function, executed once per CSV row. Test data lives outside the code."""
import csv
import os
from pathlib import Path

import pytest

from automation.pages.login_page import LoginPage

DEFAULT = Path(__file__).resolve().parents[1] / "test_data" / "login_data.csv"
DATASET = Path(os.getenv("QA_LOGIN_DATASET", DEFAULT))


def load_rows():
    if not DATASET.exists():
        raise FileNotFoundError(f"Login dataset not found: {DATASET}")
    with open(DATASET, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, raw in enumerate(reader, start=1):
            row = {(k or "").strip().lower().replace(" ", "_"): (v or "").strip() for k, v in raw.items()}
            missing = [c for c in ("username", "password", "expected_outcome") if c not in row]
            if missing:
                raise ValueError(f"{DATASET.name}: missing column(s) {missing}")
            expected = row["expected_outcome"].lower()
            if expected not in ("success", "failure"):
                raise ValueError(f"{DATASET.name} row {i}: expected_outcome must be success/failure, got {expected!r}")
            rows.append(pytest.param(i, row["username"], row["password"], expected, id=f"row{i}-{row['username'] or 'empty'}-{expected}"))
    if not rows:
        raise ValueError(f"{DATASET.name} contains no data rows")
    return rows


@pytest.mark.parametrize("row_no,username,password,expected", load_rows())
def test_data_driven_login(page, evidence, row_no, username, password, expected):
    login = LoginPage(page)
    login.login(username, password)
    actual = login.wait_for_outcome()
    evidence.update({"dataset": DATASET.name, "row": row_no, "username": username or "(empty)",
                     "password": "(empty)" if not password else "(provided)", "expected_outcome": expected,
                     "actual_outcome": actual, "result": "PASS" if actual == expected else "FAIL"})
    if actual == "failure":
        evidence["error_banner"] = login.get_error_message()
    assert actual == expected, f"Row {row_no} user={username or '(empty)'!r}: expected {expected}, actual {actual}"
