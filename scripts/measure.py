"""Run all fixture cases end to end and write docs/results.md (verdicts, calls, tokens, cost, time, verify issues).

Usage: cd backend && python ../scripts/measure.py
Re-run after switching .env to Token Factory so the README numbers match the submitted setup.
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models import Case, Session, init_db  # noqa: E402
from app.pipeline.run import run_case  # noqa: E402

SAMPLES = ROOT / "samples" / "claimback"
EXPECTED = {"case_a": "contestable", "case_b": "contestable", "case_c": "likely_valid", "case_d": "contestable"}


def main():
    init_db()
    rows = []
    for name, expected in EXPECTED.items():
        files = [SAMPLES / "policy_wording.pdf", *sorted((SAMPLES / name).iterdir())]
        t0 = time.monotonic()
        try:
            r = run_case(files)
        except Exception as e:  # one failed case shouldn't hide the others
            rows.append(f"| {name[-1].upper()} | {expected} | error: {str(e)[:60]} | | | | | |")
            continue
        secs = time.monotonic() - t0
        issues = sum(len(v) for v in r.issues.values())
        pack = "3 drafts" if r.pack else "none"
        ok = "yes" if r.verdict.outcome == expected else "**no**"
        rows.append(f"| {name[-1].upper()} | {expected} | {r.verdict.outcome} ({r.verdict.confidence}) | {ok} | {pack} "
                    f"| {issues} | {r.cost.calls} / {(r.cost.input_tokens + r.cost.output_tokens) / 1000:.1f}k "
                    f"/ ${r.cost.usd:.4f} | {secs / 60:.1f} min |")
        print(rows[-1], flush=True)
        with Session.begin() as s:
            s.delete(s.get(Case, r.case_id))
    out = ROOT / "docs" / "results.md"
    out.write_text(
        f"# Results on synthetic fixtures\n\nRun {datetime.now():%Y-%m-%d %H:%M} against `{os.environ['NEBIUS_BASE_URL']}`.\n\n"
        "| Case | Expected | Verdict | Correct | Pack | Verify issues | Calls / tokens / cost | Time |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n"
    )
    print("wrote", out)


if __name__ == "__main__":
    main()
