from datetime import date

from app.pipeline.verify import verify

CLAUSES = {"1.1", "3.2", "3.3", "4.1"}
DATES = {date(2023, 5, 15), date(2025, 5, 15), date(2026, 7, 20)}
URLS = {"https://irdai.gov.in/circular-123"}

CLEAN = ("Under clause 3.2 the waiting period ended on 15 May 2025, well before admission on 20-Jul-2026. "
         "Clauses 1.1 and 4.1 do not apply. See https://irdai.gov.in/circular-123.")


def test_clean_draft_passes():
    assert verify(CLEAN, CLAUSES, DATES, URLS) == []


def test_planted_clause_date_and_url_are_flagged():
    bad = CLEAN + " Clause 7.4 also applies. The policy began on 2023-05-16. See https://irdai.gov.in/fake-rule."
    flagged = {(i.kind, i.value) for i in verify(bad, CLAUSES, DATES, URLS)}
    assert flagged == {("clause", "7.4"), ("date", "2023-05-16"), ("url", "https://irdai.gov.in/fake-rule.")}


def test_clause_lists_and_date_formats():
    text = "Clauses 3.2, 3.3 & 9.1 apply from 15/05/2023 and May 15, 2025 to 1 January 2026."
    flagged = {(i.kind, i.value) for i in verify(text, CLAUSES, DATES, URLS)}
    assert flagged == {("clause", "9.1"), ("date", "1 January 2026")}
