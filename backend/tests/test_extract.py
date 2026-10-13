from datetime import date

import pytest

from app.pipeline.extract import classify, extract_medical_facts, extract_rejection
from app.pipeline.ingest import ingest
from conftest import SAMPLES, needs_llm

pytestmark = needs_llm

CASES = {
    "case_a": dict(claim_no="NGI-CL-2026-40112", policy_last4="1234", start=date(2023, 3, 1),
                   reason="pre_existing", clauses={"1.1", "4.1"}, admission=date(2026, 6, 10),
                   history_contains="1 yr", summary="discharge_summary.pdf"),
    "case_b": dict(claim_no="NGI-CL-2026-40987", policy_last4="7760", start=date(2023, 5, 15),
                   reason="waiting_period", clauses={"3.2"}, admission=date(2026, 7, 20),
                   history_contains=None, summary="discharge_summary.pdf"),
    "case_c": dict(claim_no="NGI-CL-2026-41530", policy_last4="3019", start=date(2025, 11, 1),
                   reason="waiting_period", clauses={"3.2"}, admission=date(2026, 8, 5),
                   history_contains=None, summary="discharge_summary.pdf"),
    "case_d": dict(claim_no="NGI-CL-2026-42277", policy_last4="0551", start=date(2022, 1, 10),
                   reason="not_medically_necessary", clauses={"4.3"}, admission=date(2026, 9, 1),
                   history_contains=None, summary="discharge_summary_photo.png"),
}


def test_classify_policy(case_id):
    assert classify(ingest(SAMPLES / "policy_wording.pdf", case_id), case_id) == "policy"


@pytest.mark.parametrize("name", CASES)
def test_case_extraction(name, case_id):
    exp = CASES[name]
    letter = ingest(SAMPLES / name / "rejection_letter.pdf", case_id)
    summary = ingest(SAMPLES / name / exp["summary"], case_id)
    assert classify(letter, case_id) == "rejection_letter"
    assert classify(summary, case_id) == "discharge_summary"

    r = extract_rejection(letter, case_id)
    assert r.claim_no == exp["claim_no"]
    assert r.policy_no_masked == "****" + exp["policy_last4"]
    assert r.policy_start_date == exp["start"]
    assert r.reason_type == exp["reason"]
    assert set(r.cited_clauses) == exp["clauses"]

    m = extract_medical_facts(summary, case_id)
    assert m.admission_date == exp["admission"]
    if exp["history_contains"]:
        assert any(exp["history_contains"] in h for h in m.history_mentioned)


def test_masking_ignores_llm():
    from app.models import mask_policy_no
    assert mask_policy_no("NGI/SHP/2023/00481234") == "****1234"
    assert mask_policy_no("****1234") == "****1234"
