import csv
import io
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.schemas.schemas import RunRequest
from app.services.execution import runner

router = APIRouter(tags=["data-driven"])
REQUIRED = ["username", "password", "expected_outcome"]
MAX_BYTES, MAX_ROWS = 200_000, 100


def read_dataset(name: str) -> tuple[list[dict], list[str]]:
    path = settings.TEST_DATA_DIR / name
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = [(c or "").strip().lower().replace(" ", "_") for c in (reader.fieldnames or [])]
        rows = [{(k or "").strip().lower().replace(" ", "_"): (v or "") for k, v in row.items()} for row in reader]
    return rows, cols


@router.get("/api/test-data")
def get_test_data(dataset: str = "login_data.csv"):
    available = runner.list_datasets()
    if dataset not in available:
        raise HTTPException(404, f"Dataset not found. Available: {available}")
    rows, cols = read_dataset(dataset)
    return {"dataset": dataset, "available_datasets": available, "data": rows, "columns": cols}


def validate_csv(raw: bytes) -> list[dict]:
    if len(raw) > MAX_BYTES:
        raise HTTPException(400, f"File too large (max {MAX_BYTES // 1000} KB).")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded text.")
    reader = csv.DictReader(io.StringIO(text))
    cols = [(c or "").strip().lower().replace(" ", "_") for c in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        raise HTTPException(400, f"Missing required column(s): {missing}. Found: {cols}")
    rows = [{(k or "").strip().lower().replace(" ", "_"): (v or "").strip() for k, v in r.items()} for r in reader]
    if not rows:
        raise HTTPException(400, "The CSV contains no data rows.")
    if len(rows) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (max {MAX_ROWS}).")
    bad = [i + 2 for i, r in enumerate(rows) if r["expected_outcome"].lower() not in ("success", "failure")]
    if bad:
        raise HTTPException(400, f"expected_outcome must be 'success' or 'failure'. Invalid on CSV line(s): {bad[:10]}")
    return rows


@router.post("/api/test-data/upload")
async def upload_test_data(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    if not name.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted.")
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    rows = validate_csv(await file.read(MAX_BYTES + 1))
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=REQUIRED, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({"username": r["username"], "password": r["password"], "expected_outcome": r["expected_outcome"].lower()})
    (settings.TEST_DATA_DIR / "uploads" / safe).write_text(out.getvalue(), encoding="utf-8")
    return {"message": "Dataset validated and saved. The default dataset was not modified.", "dataset": f"uploads/{safe}", "rows": len(rows)}


@router.post("/api/data-driven/run", status_code=202)
def run_data_driven(body: RunRequest | None = None, db: Session = Depends(get_db)):
    ex = runner.start_execution(db, "data_driven", body.dataset if body else None)
    return {"execution_id": ex.execution_id, "db_id": ex.id, "status": "started", "dataset": ex.dataset}
