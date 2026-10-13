import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "claimback"

needs_llm = pytest.mark.skipif(not os.environ.get("NEBIUS_API_KEY"), reason="no LLM key in .env")


@pytest.fixture(scope="session")
def db():
    from app.models import init_db
    init_db()


@pytest.fixture
def case_id(db):
    from app.models import Case, Session
    with Session.begin() as s:
        case = Case()
        s.add(case)
    yield case.id
    with Session.begin() as s:
        s.delete(s.get(Case, case.id))  # cascades to clauses, documents, llm_calls
