"""Step 6: all date maths, in code only. Never ask an LLM to do this."""
import calendar
import re
from datetime import date, timedelta

from pydantic import BaseModel

_PERIOD = re.compile(r"(\d+)\s*(day|month|mo|year|yr)s?\b", re.I)
_UNIT = {"day": "days", "month": "months", "mo": "months", "year": "years", "yr": "years"}


def parse_period(text: str) -> tuple[int, str] | None:
    """First duration in text, e.g. '24 months of continuous coverage' -> (24, 'months')."""
    m = _PERIOD.search(text)
    return (int(m.group(1)), _UNIT[m.group(2).lower()]) if m else None


def shift(d: date, n: int, unit: str) -> date:
    """d moved by n days/months/years (n may be negative); month ends clamp, e.g. 31 Jan + 1 month = 28/29 Feb."""
    if unit == "days":
        return d + timedelta(days=n)
    months = d.month - 1 + n * (12 if unit == "years" else 1)
    y, m = d.year + months // 12, months % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def full_years(start: date, on: date) -> int:
    return on.year - start.year - ((on.month, on.day) < (start.month, start.day))


class ComputedDates(BaseModel):
    policy_start: date
    admission_date: date
    days_policy_to_admission: int
    coverage_full_years: int
    waiting_period: str | None  # e.g. "24 months"
    waiting_period_ends: date | None
    waiting_period_over: bool | None
    history_onsets: dict[str, date | None]  # verbatim history phrase -> estimated onset
    history_onset_before_policy: dict[str, bool | None]


def compute_dates(policy_start: date, admission: date, waiting_clause_text: str | None,
                  history: list[str]) -> ComputedDates:
    period = parse_period(waiting_clause_text) if waiting_clause_text else None
    ends = shift(policy_start, *period) if period else None
    # ponytail: onset = admission minus the first duration in the phrase ("since 1 yr"); absolute dates
    # in history phrases ("since 2019") aren't parsed yet.
    onsets = {}
    for h in history:
        p = parse_period(h)
        onsets[h] = shift(admission, -p[0], p[1]) if p else None
    return ComputedDates(
        policy_start=policy_start,
        admission_date=admission,
        days_policy_to_admission=(admission - policy_start).days,
        coverage_full_years=full_years(policy_start, admission),
        waiting_period=f"{period[0]} {period[1]}" if period else None,
        waiting_period_ends=ends,
        waiting_period_over=admission >= ends if ends else None,
        history_onsets=onsets,
        history_onset_before_policy={h: (o < policy_start if o else None) for h, o in onsets.items()},
    )
