from fastapi.testclient import TestClient

import app.main as main
from conftest import SAMPLES


def test_upload_track_delete(db, monkeypatch):
    monkeypatch.setattr(main, "_process", lambda case_id, files: None)  # no LLM calls here
    c = TestClient(main.app)

    bad = c.post("/cases", files=[("files", ("notes.exe", b"x", "application/octet-stream"))])
    assert bad.status_code == 400

    pdf = (SAMPLES / "case_a" / "rejection_letter.pdf").read_bytes()
    r = c.post("/cases", files=[("files", ("../../evil name.pdf", pdf, "application/pdf"))])
    case_id = r.json()["id"]
    saved = list((main.UPLOADS / case_id).rglob("*.pdf"))
    assert [p.relative_to(main.UPLOADS / case_id).as_posix() for p in saved] == ["0/evil_name.pdf"]

    assert c.get(f"/cases/{case_id}").json()["status"] == "processing"
    assert c.post(f"/cases/{case_id}/verify", json={"text": "x"}).status_code == 409

    steps = c.put(f"/cases/{case_id}/tracker", json={"stage": "grievance", "filed_on": "2026-10-01"}).json()
    assert steps[1]["opens_on"] == "2026-10-15"
    assert c.put(f"/cases/{case_id}/tracker", json={"stage": "nope", "filed_on": None}).status_code == 400

    assert c.delete(f"/cases/{case_id}").status_code == 204
    assert not (main.UPLOADS / case_id).exists()
    assert c.get(f"/cases/{case_id}").status_code == 404
