from datetime import date

from app.domain.dates import compute_dates, full_years, parse_period, shift


def test_parse_period():
    assert parse_period("excluded until 24 months of continuous coverage") == (24, "months")
    assert parse_period("within 30 days of the first policy") == (30, "days")
    assert parse_period("k/c/o HTN 2 yrs") == (2, "years")
    assert parse_period("no duration here") is None


def test_shift_clamps_month_end_and_goes_back():
    assert shift(date(2024, 1, 31), 1, "months") == date(2024, 2, 29)
    assert shift(date(2026, 6, 10), -1, "years") == date(2025, 6, 10)
    assert shift(date(2024, 2, 29), 1, "years") == date(2025, 2, 28)


def test_full_years():
    assert full_years(date(2023, 5, 15), date(2025, 5, 14)) == 1
    assert full_years(date(2023, 5, 15), date(2025, 5, 15)) == 2


def test_case_a_history_began_after_policy_start():
    d = compute_dates(date(2023, 3, 1), date(2026, 6, 10), "36 months of continuous coverage",
                      ["k/c/o Type 2 DM since 1 yr"])
    assert d.history_onsets["k/c/o Type 2 DM since 1 yr"] == date(2025, 6, 10)
    assert d.history_onset_before_policy["k/c/o Type 2 DM since 1 yr"] is False
    assert d.waiting_period_over is True


def test_case_b_waiting_period_ended():
    d = compute_dates(date(2023, 5, 15), date(2026, 7, 20), "until 24 months of continuous coverage", [])
    assert d.waiting_period_ends == date(2025, 5, 15)
    assert d.waiting_period_over is True
    assert d.coverage_full_years == 3


def test_case_c_waiting_period_running():
    d = compute_dates(date(2025, 11, 1), date(2026, 8, 5), "until 24 months of continuous coverage", [])
    assert d.waiting_period_ends == date(2027, 11, 1)
    assert d.waiting_period_over is False
    assert d.days_policy_to_admission == 277


def test_tracker_clocks_start_at_grievance():
    from app.domain.dates import tracker
    today = date(2026, 10, 20)
    before = {s.stage: s for s in tracker({}, today)}
    assert before["grievance"].open and not before["bima_bharosa"].open and before["ombudsman"].opens_on is None
    after = {s.stage: s for s in tracker({"grievance": date(2026, 10, 1)}, today)}
    assert after["bima_bharosa"].opens_on == date(2026, 10, 15) and after["bima_bharosa"].open
    assert after["ombudsman"].opens_on == date(2026, 10, 31) and not after["ombudsman"].open
