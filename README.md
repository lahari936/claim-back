# ClaimBack

Health claim appeal agent: rejection letter + policy + hospital papers → verdict + escalation pack
(insurer grievance → Bima Bharosa → Insurance Ombudsman). Spec: [docs/SPEC.md](docs/SPEC.md).

## Setup

```bash
cp .env.example .env            # fill in keys
docker compose up -d db         # Postgres + pgvector
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
python scripts/smoke_models.py  # check every model responds
python scripts/make_samples.py  # regenerate synthetic fixtures
cd backend && python -m pytest  # LLM tests skip without a key
```
