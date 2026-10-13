"""Step 11: check every clause number, date and URL in a draft against the index, computed dates and sources."""
import re
from datetime import date, datetime

from pydantic import BaseModel

_CLAUSES = re.compile(r"(?i)\bclauses?\s+(\d+(?:\.\d+)*(?:\s*(?:,|and|&|/)\s*\d+(?:\.\d+)*)*)")
_URL = re.compile(r"https?://[^\s)\]>\"']+")
_DATE_FORMATS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), ["%Y-%m-%d"]),
    (re.compile(r"\b\d{1,2}[-/ ][A-Za-z]{3,9},?[-/ ]\d{4}\b"), ["%d-%b-%Y", "%d %b %Y", "%d %B %Y", "%d-%B-%Y", "%d/%b/%Y"]),
    (re.compile(r"\b[A-Za-z]{3,9} \d{1,2},? \d{4}\b"), ["%B %d %Y", "%b %d %Y"]),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), ["%d/%m/%Y"]),
]


class Issue(BaseModel):
    kind: str  # "clause" | "date" | "url"
    value: str


def _parse(s: str, fmts: list[str]) -> date | None:
    s = s.replace(",", "")
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def verify(text: str, clause_nos: set[str], dates: set[date], urls: set[str]) -> list[Issue]:
    issues = []
    for group in _CLAUSES.findall(text):
        for no in re.findall(r"\d+(?:\.\d+)*", group):
            if no not in clause_nos:
                issues.append(Issue(kind="clause", value=no))
    for rx, fmts in _DATE_FORMATS:
        for raw in rx.findall(text):
            d = _parse(raw, fmts)
            if d and d not in dates:
                issues.append(Issue(kind="date", value=raw))
    for url in _URL.findall(text):
        if url.rstrip(".,;:") not in urls:
            issues.append(Issue(kind="url", value=url))
    return issues
