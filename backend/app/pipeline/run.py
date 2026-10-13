"""Runs the full pipeline (spec section 5) for one case.

CLI: python -m app.pipeline.run ../samples/claimback/policy_wording.pdf ../samples/claimback/case_a/*
"""
import sys
from datetime import date
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import func, select

from app.domain.dates import ComputedDates, compute_dates
from app.domain.policy import index_policy
from app.models import (Case, ClauseRow, Document, LLMCall, MedicalFacts, Pack, Rejection, Session, Verdict,
                        init_db)
from app.pipeline import reason
from app.pipeline.extract import classify, extract_medical_facts, extract_rejection
from app.pipeline.ingest import ingest
from app.pipeline.verify import Issue, verify


class Cost(BaseModel):
    calls: int
    input_tokens: int
    output_tokens: int
    usd: float


class CaseResult(BaseModel):
    case_id: str
    documents: dict[str, str]  # filename -> doc_type
    rejection: Rejection
    facts: MedicalFacts
    dates: ComputedDates
    clauses: list[dict]  # retrieved: id, clause_no, tag, text
    sources: list[dict]  # id, title, url
    verdict: Verdict
    pack: Pack | None
    no_pack_reason: str | None
    issues: dict[str, list[Issue]]  # "verdict" | "grievance" | ... -> problems found by verify
    cost: Cost


def case_cost(case_id: str) -> Cost:
    with Session() as s:
        n, tin, tout, usd = s.execute(select(func.count(), func.coalesce(func.sum(LLMCall.input_tokens), 0),
                                             func.coalesce(func.sum(LLMCall.output_tokens), 0),
                                             func.coalesce(func.sum(LLMCall.cost), 0.0))
                                      .where(LLMCall.case_id == case_id)).one()
    return Cost(calls=n, input_tokens=tin, output_tokens=tout, usd=usd)


def run_case(files: list[Path], case_id: str | None = None) -> CaseResult:
    if case_id is None:
        with Session.begin() as s:
            case = Case()
            s.add(case)
        case_id = case.id

    texts: dict[str, str] = {}  # doc_type -> text (first file of each type wins)
    docs: dict[str, str] = {}
    for f in files:
        text = ingest(f, case_id)
        doc_type = classify(text, case_id)
        docs[f.name] = doc_type
        texts.setdefault(doc_type, text)
        with Session.begin() as s:
            s.add(Document(case_id=case_id, filename=f.name, doc_type=doc_type, text=text))
    missing = {"rejection_letter", "policy", "discharge_summary"} - texts.keys()
    if missing:
        raise ValueError(f"missing documents: {', '.join(sorted(missing))}")

    rej = extract_rejection(texts["rejection_letter"], case_id)
    facts = extract_medical_facts(texts["discharge_summary"], case_id)
    if rej.policy_start_date is None:
        raise ValueError("policy start date not found in the rejection letter; add the policy schedule")
    index_policy(texts["policy"], case_id)

    clauses = reason.retrieve(case_id, rej)
    dates = compute_dates(rej.policy_start_date, facts.admission_date, reason.waiting_clause_text(clauses),
                          facts.history_mentioned)
    sources = reason.research(case_id, rej)
    ctx = reason.context(rej, facts, dates, clauses, sources)
    v = reason.verdict(case_id, ctx)

    pack, no_pack_reason = None, None
    if v.outcome == "likely_valid":
        no_pack_reason = "The rejection looks valid on the policy wording and dates, so no appeal pack was drafted."
    else:
        cited = [s for s in sources if s.id in v.source_ids]
        pack = reason.draft(case_id, reason.context(rej, facts, dates, clauses, cited), v)

    with Session() as s:
        indexed = set(s.scalars(select(ClauseRow.clause_no).where(ClauseRow.case_id == case_id)))
    ok_dates = {d for d in [dates.policy_start, dates.admission_date, dates.waiting_period_ends, rej.rejection_date,
                            facts.discharge_date, date.today(), *dates.history_onsets.values()] if d}
    urls = {s.url for s in sources if s.id in v.source_ids}
    issues = {"verdict": verify(" ".join(v.reasons), indexed, ok_dates, urls)
              + [Issue(kind="clause_id", value=str(i)) for i in v.clause_ids if i not in {c.id for c in clauses}]
              + [Issue(kind="source_id", value=str(i)) for i in v.source_ids if i not in {s.id for s in sources}]}
    if pack:
        issues |= {k: verify(t, indexed, ok_dates, urls) for k, t in pack.model_dump().items()}

    result = CaseResult(
        case_id=case_id, documents=docs, rejection=rej, facts=facts, dates=dates,
        clauses=[{"id": c.id, "clause_no": c.clause_no, "tag": c.tag, "text": c.text} for c in clauses],
        sources=[{"id": s.id, "title": s.title, "url": s.url} for s in sources],
        verdict=v, pack=pack, no_pack_reason=no_pack_reason, issues=issues, cost=case_cost(case_id),
    )
    with Session.begin() as s:
        s.get(Case, case_id).result = result.model_dump(mode="json")
    return result


if __name__ == "__main__":
    init_db()
    r = run_case([Path(p) for p in sys.argv[1:]])
    print(f"case {r.case_id}\ndocuments: {r.documents}")
    print(f"rejection: {r.rejection.reason_type} citing {r.rejection.cited_clauses}")
    print(f"dates: {r.dates.model_dump_json(indent=1)}")
    print(f"clauses: {[c['clause_no'] for c in r.clauses]}  sources: {len(r.sources)}")
    print(f"\nVERDICT: {r.verdict.model_dump_json(indent=1)}")
    if r.pack:
        for k, t in r.pack.model_dump().items():
            print(f"\n----- {k} ({len(t.split())} words) -----\n{t}")
    else:
        print(f"\nNO PACK: {r.no_pack_reason}")
    print(f"\nissues: { {k: [i.model_dump() for i in v] for k, v in r.issues.items()} }")
    print(f"cost: {r.cost}")
