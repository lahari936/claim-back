import logging
import re
import shutil
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select

from app.domain.dates import tracker
from app.models import Case, ClauseRow, Document, Session, init_db
from app.pipeline.run import CaseResult, allowed, case_cost, run_case
from app.pipeline.verify import verify

log = logging.getLogger(__name__)
UPLOADS = Path(__file__).resolve().parents[1] / "uploads"
MAX_FILE_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
STAGES = {"grievance", "bima_bharosa", "ombudsman"}


@asynccontextmanager
async def lifespan(_):
    init_db()
    yield


app = FastAPI(title="ClaimBack", lifespan=lifespan)
# ponytail: wide-open CORS for the hackathon demo; pin to the Vercel origin before real users.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


def _get(s, case_id: str) -> Case:
    case = s.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return case


def _process(case_id: str, files: list[Path]) -> None:
    try:
        run_case(files, case_id)
    except Exception as e:  # surface the failure to the UI instead of leaving the case spinning
        log.exception("case failed")
        with Session.begin() as s:
            case = s.get(Case, case_id)
            if case:  # may have been deleted mid-run
                case.status, case.error = "error", str(e)[:500]


@app.post("/cases")
async def create_case(files: list[UploadFile], background: BackgroundTasks):
    if not files:
        raise HTTPException(400, "upload at least one file")
    for f in files:
        if Path(f.filename or "").suffix.lower() not in ALLOWED_SUFFIXES:
            raise HTTPException(400, f"{f.filename}: only PDF or image files")
    with Session.begin() as s:
        case = Case(status="processing", stage="Uploading")
        s.add(case)
    folder = UPLOADS / case.id
    folder.mkdir(parents=True)
    paths = []
    for i, f in enumerate(files):
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            shutil.rmtree(folder)
            with Session.begin() as s:
                s.delete(s.get(Case, case.id))
            raise HTTPException(413, f"{f.filename}: larger than 15 MB")
        name = Path(f.filename)
        # Never trust the client filename for the path: sanitise it, and number folders so duplicates can't clash.
        path = folder / str(i) / f"{re.sub(r'[^\w-]', '_', name.stem)[:60]}{name.suffix.lower()}"
        path.parent.mkdir()
        path.write_bytes(data)
        paths.append(path)
    background.add_task(_process, case.id, paths)
    return {"id": case.id}


@app.get("/cases")
def list_cases():
    with Session() as s:
        cases = s.scalars(select(Case).order_by(Case.created_at.desc())).all()
        return [{"id": c.id, "created_at": c.created_at, "status": c.status,
                 "claim_no": (c.result or {}).get("rejection", {}).get("claim_no"),
                 "insurer": (c.result or {}).get("rejection", {}).get("insurer"),
                 "outcome": (c.result or {}).get("verdict", {}).get("outcome")} for c in cases]


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    with Session() as s:
        case = _get(s, case_id)
        docs = s.scalars(select(Document).where(Document.case_id == case_id)).all()
        return {"id": case.id, "created_at": case.created_at, "status": case.status, "stage": case.stage,
                "error": case.error, "result": case.result,
                "documents": [{"filename": d.filename, "doc_type": d.doc_type} for d in docs],
                "cost": case_cost(case_id),
                "tracker": tracker({k: date.fromisoformat(v) for k, v in (case.tracker or {}).items()}, date.today())}


@app.get("/cases/{case_id}/clauses/{clause_no}")
def get_clause(case_id: str, clause_no: str):
    with Session() as s:
        row = s.scalar(select(ClauseRow).where(ClauseRow.case_id == case_id, ClauseRow.clause_no == clause_no))
        if not row:
            raise HTTPException(404, "clause not in this policy")
        return {"id": row.id, "clause_no": row.clause_no, "tag": row.tag, "text": row.text}


class VerifyIn(BaseModel):
    text: str


@app.post("/cases/{case_id}/verify")
def reverify(case_id: str, body: VerifyIn):
    """Re-check an edited draft against the same index, dates and sources."""
    with Session() as s:
        case = _get(s, case_id)
        if not case.result:
            raise HTTPException(409, "case still processing")
        r = CaseResult.model_validate(case.result)
    return verify(body.text, *allowed(r))


class TrackerIn(BaseModel):
    stage: str
    filed_on: date | None  # None clears the stage


@app.put("/cases/{case_id}/tracker")
def set_tracker(case_id: str, body: TrackerIn):
    if body.stage not in STAGES:
        raise HTTPException(400, "unknown stage")
    with Session.begin() as s:
        case = _get(s, case_id)
        t = dict(case.tracker or {})
        if body.filed_on:
            t[body.stage] = body.filed_on.isoformat()
        else:
            t.pop(body.stage, None)
        case.tracker = t
    return tracker({k: date.fromisoformat(v) for k, v in t.items()}, date.today())


@app.delete("/cases/{case_id}", status_code=204)
def delete_case(case_id: str):
    with Session.begin() as s:
        s.delete(_get(s, case_id))  # DB cascades to documents, clauses, sources, llm_calls
    shutil.rmtree(UPLOADS / case_id, ignore_errors=True)
