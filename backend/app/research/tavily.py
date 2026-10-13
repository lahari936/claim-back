"""Tavily search; every result is stored in `sources` so drafts can cite only stored rows."""
import os

from tavily import TavilyClient

from app.models import Session, Source

tv = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

INSURANCE_DOMAINS = ["irdai.gov.in", "bimabharosa.irdai.gov.in", "cioins.co.in"]


def search_official(query: str, case_id: str, domains: list[str] = INSURANCE_DOMAINS) -> list[Source]:
    res = tv.search(query=query, include_domains=domains, search_depth="advanced", max_results=5)
    rows = [Source(case_id=case_id, title=r["title"], url=r["url"], content=r["content"]) for r in res["results"]]
    with Session.begin() as s:
        s.add_all(rows)
    return rows
