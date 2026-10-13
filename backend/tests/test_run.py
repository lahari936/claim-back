"""Phase 3 gate: full pipeline on cases A-C (slow: real LLM + Tavily calls)."""
import pytest

from app.pipeline.run import run_case
from conftest import SAMPLES, needs_llm

pytestmark = needs_llm

EXPECTED = {"case_a": "contestable", "case_b": "contestable", "case_c": "likely_valid"}


@pytest.mark.parametrize("name", EXPECTED)
def test_full_case(name, case_id):
    r = run_case([SAMPLES / "policy_wording.pdf", *sorted((SAMPLES / name).iterdir())], case_id)
    assert r.verdict.outcome == EXPECTED[name], r.verdict.reasons
    if name == "case_c":
        assert r.pack is None and r.no_pack_reason
    else:
        assert r.pack is not None
        assert all(not v for v in r.issues.values()), r.issues
        assert "computed_dates" not in r.pack.grievance
    assert r.cost.calls > 0
