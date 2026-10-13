from app.domain.policy import get_clause, index_policy, search_clauses, split_clauses
from app.pipeline.ingest import ingest
from conftest import SAMPLES, needs_llm

EXPECTED_NOS = ["1", "1.1", "1.2", "1.3", "1.4", "2", "2.1", "2.2", "3", "3.1", "3.2", "3.3",
                "4", "4.1", "4.2", "4.3", "5", "5.1", "6", "6.1", "6.2"]


def test_split_keeps_numbers_and_full_wording():
    clauses = dict(split_clauses(ingest(SAMPLES / "policy_wording.pdf", None)))
    assert list(clauses) == EXPECTED_NOS
    assert "36 months prior to the effective date of the first policy" in clauses["1.1"]
    assert clauses["3.2"].endswith("sinusitis.")


@needs_llm
def test_index_tags_and_search(case_id):
    clauses = {c.clause_no: c for c in index_policy(ingest(SAMPLES / "policy_wording.pdf", case_id), case_id)}
    assert clauses["1.1"].tag == "definition"
    assert clauses["3.2"].tag == "waiting_period"
    assert clauses["4.1"].tag == "exclusion"
    assert get_clause(case_id, "3.2").text == clauses["3.2"].text
    assert get_clause(case_id, "9.9") is None
    top = [r.clause_no for r in search_clauses(case_id, "definition of pre-existing disease", k=3)]
    assert "1.1" in top
