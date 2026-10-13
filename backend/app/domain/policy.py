"""Step 4: policy clause index. Split in code (exact wording kept), tag with the fast model, embed into pgvector."""
import re

from sqlalchemy import select

from app.llm.client import call_json, embed
from app.models import Clause, ClauseRow, ClauseTags, Session

# ponytail: clause starts are lines like "3.2 ..." or "4. ..."; a wrapped line starting "2.5 lakh" would split
# wrongly. Fall back to LLM splitting if real policies break this.
_CLAUSE_START = re.compile(r"^\s*(\d+\.\d+(?:\.\d+)*|\d+\.)\s+(.*)")

TAG = ("Tag each policy clause with one of: definition, exclusion, waiting_period, sub_limit, procedure, other. "
       "Return {\"tags\": {clause_no: tag}} for every clause_no given.")


def split_clauses(text: str) -> list[tuple[str, str]]:
    clauses: list[list[str]] = []
    for line in text.splitlines():
        m = _CLAUSE_START.match(line)
        if m:
            clauses.append([m.group(1).rstrip("."), m.group(2).strip()])
        elif clauses and line.strip():
            clauses[-1][1] += " " + line.strip()
    return [(no, body) for no, body in clauses]


def index_policy(text: str, case_id: str) -> list[Clause]:
    parts = split_clauses(text)
    listing = "\n".join(f"{no}: {body[:300]}" for no, body in parts)
    tags = call_json("fast", TAG, listing, ClauseTags, case_id).tags
    clauses = [Clause(clause_no=no, text=body, tag=tags.get(no, "other")) for no, body in parts]
    vectors = embed([f"{c.clause_no} {c.text}" for c in clauses], case_id)
    with Session.begin() as s:
        s.add_all(ClauseRow(case_id=case_id, clause_no=c.clause_no, text=c.text, tag=c.tag, embedding=v)
                  for c, v in zip(clauses, vectors))
    return clauses


def get_clause(case_id: str, clause_no: str) -> ClauseRow | None:
    with Session() as s:
        return s.scalar(select(ClauseRow).where(ClauseRow.case_id == case_id, ClauseRow.clause_no == clause_no))


def search_clauses(case_id: str, query: str, k: int = 5) -> list[ClauseRow]:
    [q] = embed([query], case_id)
    with Session() as s:
        return list(s.scalars(select(ClauseRow).where(ClauseRow.case_id == case_id)
                              .order_by(ClauseRow.embedding.cosine_distance(q)).limit(k)))
