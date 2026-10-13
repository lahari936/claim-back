"""Steps 7-10: retrieve clauses, research, verdict, draft pack."""
import json
import re

from app.domain.dates import ComputedDates
from app.domain.policy import get_clause, search_clauses
from app.llm.client import call_json
from app.models import ClauseRow, MedicalFacts, Pack, Queries, Rejection, Source, Verdict
from app.research.tavily import search_official

_CLAUSE_REF = re.compile(r"(?i)clauses?\s+(\d+(?:\.\d+)+)")


def retrieve(case_id: str, rej: Rejection) -> list[ClauseRow]:
    """Cited clauses, clauses they reference ("as defined in clause 1.3"), and the closest definitions."""
    found: dict[str, ClauseRow] = {}
    todo = list(rej.cited_clauses)
    while todo:
        no = todo.pop()
        if no in found or not (row := get_clause(case_id, no)):
            continue
        found[no] = row
        todo += _CLAUSE_REF.findall(row.text)
    for row in search_clauses(case_id, f"definition: {rej.reason_text}", k=8):
        if row.tag == "definition" and len([r for r in found.values() if r.tag == "definition"]) < 3:
            found.setdefault(row.clause_no, row)
    return sorted(found.values(), key=lambda r: [int(x) for x in r.clause_no.split(".")])


def waiting_clause_text(clauses: list[ClauseRow]) -> str | None:
    return next((c.text for c in clauses if c.tag == "waiting_period"), None)


QUERIES = ("You research Indian health-insurance regulation for a policyholder appealing a claim rejection. "
           "Write 2 short web search queries for IRDAI rules, circulars or Ombudsman guidance on this rejection "
           "type (e.g. IRDAI definition of pre-existing disease, waiting period rules, moratorium, grievance timelines).")


def research(case_id: str, rej: Rejection) -> list[Source]:
    qs = call_json("agent", QUERIES, f"Rejection type: {rej.reason_type}\nReason: {rej.reason_text}", Queries, case_id)
    by_url: dict[str, Source] = {}
    for q in qs.queries[:2]:
        for s in search_official(q, case_id):
            by_url.setdefault(s.url, s)
    return list(by_url.values())


def context(rej: Rejection, facts: MedicalFacts, dates: ComputedDates, clauses: list[ClauseRow],
             sources: list[Source]) -> str:
    return json.dumps({
        "rejection": rej.model_dump(mode="json"),
        "medical_facts": facts.model_dump(mode="json"),
        "computed_dates": dates.model_dump(mode="json"),
        "clauses": [{"clause_id": c.id, "clause_no": c.clause_no, "tag": c.tag, "text": c.text} for c in clauses],
        "sources": [{"source_id": s.id, "title": s.title, "url": s.url, "excerpt": s.content[:600]} for s in sources],
    }, indent=1)


VERDICT = ("You are reviewing an insurer's claim rejection for the policyholder. Using only the clauses, medical "
           "facts and computed dates given, decide whether the stated reason holds. computed_dates is exact; "
           "never recompute dates. Quote clause numbers. If the facts support the insurer, say so plainly "
           "(outcome likely_valid). Do not give medical advice. clause_ids and source_ids must be ids from the "
           "input. Each reason must cite a clause number or a fact. Cite a source_id only if its excerpt directly "
           "supports a reason; an unrelated product brochure or policy is not support, so leave source_ids empty "
           "rather than stretch. missing_documents: papers that would strengthen the case.")


def verdict(case_id: str, ctx: str) -> Verdict:
    return call_json("reason", VERDICT, ctx, Verdict, case_id)


PACK = ("Draft three texts for the policyholder, using only the clauses, facts, computed dates and sources given. "
        "Quote only clause numbers that appear in the input clauses, only dates that appear in the input, and only "
        "URLs from the input sources. Write dates like 10 June 2026. Write for a human reader: never mention JSON "
        "field names such as computed_dates or clause_id. Use placeholders like [Your name] for anything not given.\n"
        "grievance: a firm, polite letter to the insurer's Grievance Redressal Officer stating the claim number, "
        "the stated reason, why it does not apply (citing clauses and facts), and the relief sought. Under 400 words.\n"
        "bima_bharosa: a concise complaint for the IRDAI Bima Bharosa portal, to use if the insurer does not "
        "resolve the grievance within 14 days. Under 200 words.\n"
        "ombudsman: an Insurance Ombudsman complaint draft with sections: complainant, insurer, policy and claim "
        "details, facts, grounds, relief sought. Under 400 words.")


def draft(case_id: str, ctx: str, v: Verdict) -> Pack:
    return call_json("reason", PACK, ctx + "\n\nVerdict:\n" + v.model_dump_json(), Pack, case_id)
