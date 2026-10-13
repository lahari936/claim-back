# ClaimBack

**Health claim appeal agent for Indian policyholders.** Upload a claim rejection letter, the policy wording and the
hospital discharge summary. ClaimBack reads the clause the insurer cited, works out the dates in code, checks IRDAI
guidance live, and says whether the rejection is **contestable**, **likely valid** or **unclear**. If it is worth
contesting, it drafts the escalation pack: a grievance letter to the insurer, a Bima Bharosa complaint and an
Insurance Ombudsman draft. Every clause number, date and link in those drafts is checked, and anything that can't be
verified is marked red.

Built for the Nebius x NVIDIA Global AI Hackathon (Best Apps and Agents, Best Use of Tavily). Spec: [docs/SPEC.md](docs/SPEC.md).

> Drafts are for the policyholder's review. Not legal or medical advice. Nothing is filed automatically.

Scope: full rejections for pre-existing disease, waiting period, non-disclosure and "not medically necessary".
Partial deductions are out of scope.

## How it works

| Step | What happens | Where |
| --- | --- | --- |
| 1. Ingest | Digital PDFs → PyMuPDF text. Photos and scanned pages → Nemotron Omni transcription | `pipeline/ingest.py` |
| 2. Classify | Each file labelled: rejection letter, policy, discharge summary, bill, other | `pipeline/extract.py` |
| 3. Extract | Rejection (claim no, cited clauses, reason type; policy no masked in code) and medical facts | `pipeline/extract.py` |
| 4. Index policy | Clauses split in code (wording kept exact), tagged by Nemotron, embedded into pgvector | `domain/policy.py` |
| 5. Dates | Waiting-period end, years covered, when a past condition began. Pure Python, never the LLM | `domain/dates.py` |
| 6. Retrieve | Cited clauses + the clauses they reference + closest definitions | `pipeline/reason.py` |
| 7. Research | Nemotron writes queries; Tavily searches irdai.gov.in, bimabharosa.irdai.gov.in, cioins.co.in; every result stored in `sources` | `research/tavily.py` |
| 8. Verdict | Nemotron Ultra weighs facts and computed dates against the clause wording | `pipeline/reason.py` |
| 9. Draft | Grievance, Bima Bharosa and Ombudsman drafts, only if contestable or unclear | `pipeline/reason.py` |
| 10. Verify | Every clause number must be in the index, every date in the computed set, every URL in `sources` | `pipeline/verify.py` |

All model calls go through one client (`backend/app/llm/client.py`) that validates output against Pydantic schemas,
retries once on invalid JSON, and logs tokens and cost per case to `llm_calls` (shown as "Cost of this case" in the UI).
Prompts and responses are never logged.

## Nemotron models used

| Tier | Used for | Model (confirm exact IDs in your catalog) |
| --- | --- | --- |
| vision | Reading photographed or scanned documents | Nemotron 3 Nano Omni |
| fast | Classifying documents, extraction, clause tagging | Nemotron 3 Nano 30B-A3B |
| agent | Writing research queries for Tavily | Nemotron 3 Super 120B-A12B |
| reason | Verdict and escalation drafts | Nemotron 3 Ultra 550B-A55B |
| embed | Clause search in pgvector | Nemotron 3 Embed 1B |

Model IDs live in environment variables (`MODEL_*`), not code, because catalogs change. Development used the same
Nemotron family through NVIDIA's API catalog (`integrate.api.nvidia.com`); the fast tier there was Nemotron 3.5
Lightning 30B-A3B because Nano 3 was unavailable on that account.

Two things we learned about these models:
- **Reasoning output.** The answer arrives in `content` with the thinking in `reasoning_content`. The client falls back
  to the reasoning field when `content` is empty.
- **Vision needs thinking off.** With thinking on, Nano Omni looped on a full-page transcription. With a `/no_think`
  system prompt it transcribed the sample discharge photo exactly.

## Where Token Factory helped

- **One OpenAI-compatible endpoint for every tier.** Vision, extraction, research, reasoning and embeddings all go
  through one `openai` client. Switching provider or model means changing `.env`, not code.
- **Right-sized models per step.** The 550B Ultra model runs only the verdict and drafts (2 of about 11 calls per
  case); cheap steps use 30B-A3B. This keeps the cost per case low; the UI shows it per case.
- **JSON mode** (`response_format: json_object`) plus Pydantic validation gives typed outputs without extra parsing.
- _TODO before submitting: add Token Factory specifics after switching `NEBIUS_BASE_URL` (latency, cost per case
  from the UI panel, anything that helped or got in the way)._

## Other Nebius services used

- **Serverless AI endpoints**: the backend container (below).
- **Managed Service for PostgreSQL**: Nebius lists pgvector as included. Point `DATABASE_URL` at it in production.
- _TODO: confirm which of these you actually deployed on before submitting._

## Results on the synthetic fixtures

| Case | Rejection | Expected | Got | Pack |
| --- | --- | --- | --- | --- |
| A | Pre-existing; history began 1 year before admission, after the 2023 policy start | contestable | contestable (high) | 3 drafts, 0 verify issues |
| B | Waiting period; 24 months ended 15 May 2025, admission July 2026 | contestable | contestable | 3 drafts, 0 verify issues |
| C | Waiting period; 277 days covered of 24 months | likely valid | likely valid | none, with reason |
| D | Not medically necessary; discharge summary is a photo, platelet transfusion given | contestable | contestable (medium) | 3 drafts, 0 verify issues |

A full case takes about 11 model calls and 25k tokens. On NVIDIA's free tier a case took about 5 minutes end to end,
mostly the Ultra model.

All fixtures in `samples/claimback/` are synthetic: an invented insurer, people, numbers and policy wording.

## Setup

Requirements: Python 3.12+, Node 20+, Docker.

```bash
cp .env.example .env              # fill in NEBIUS_API_KEY, TAVILY_API_KEY and check the MODEL_* IDs
docker compose up -d db           # Postgres 16 + pgvector on localhost:55432
pip install -r backend/requirements.txt
cd frontend && npm install
```

| Variable | Meaning |
| --- | --- |
| `NEBIUS_BASE_URL`, `NEBIUS_API_KEY` | Token Factory (or any OpenAI-compatible Nemotron host) |
| `MODEL_VISION`, `MODEL_FAST`, `MODEL_AGENT`, `MODEL_REASON`, `MODEL_EMBED` | Model IDs from the catalog |
| `TAVILY_API_KEY` | Tavily search |
| `DATABASE_URL` | Postgres with pgvector |
| `PRICE_*` | Optional USD per 1M tokens `input,output` for the cost panel |
| `NEXT_PUBLIC_API_URL` | Backend URL for the frontend (put it in `frontend/.env.local` locally) |

Check every model responds and see which field holds the answer:

```bash
python scripts/smoke_models.py
```

## Running

```bash
cd backend && uvicorn app.main:app --port 8000      # API
cd frontend && npm run dev                          # UI on http://localhost:3000
```

The home page has **Try a synthetic sample A–D** buttons that load the fixtures into the uploader.

Command line, one case end to end:

```bash
cd backend && python -m app.pipeline.run ../samples/claimback/policy_wording.pdf ../samples/claimback/case_a/*
```

Tests (tests that call models or Tavily skip without keys; the full run takes 15–30 minutes on a free tier):

```bash
cd backend && python -m pytest
python scripts/make_samples.py    # regenerate the fixtures
```

## Deploying

### Backend → Nebius Serverless AI endpoint

The backend is a single container (`backend/Dockerfile`, listens on port 8000).

```bash
docker build -t <registry>/claimback-api:latest backend
docker push <registry>/claimback-api:latest
```

Push to Nebius [Container Registry](https://docs.nebius.com/container-registry) in the same project (no credentials
needed) or to any public registry. Then create the endpoint with the
[Nebius AI Cloud CLI](https://docs.nebius.com/serverless/endpoints/manage):

```bash
nebius ai endpoint create \
  --name claimback-api \
  --image <registry>/claimback-api:latest \
  --container-port 8000 \
  --env "NEBIUS_BASE_URL=...,NEBIUS_API_KEY=...,TAVILY_API_KEY=...,DATABASE_URL=..." \
  --env "MODEL_VISION=...,MODEL_FAST=...,MODEL_AGENT=...,MODEL_REASON=...,MODEL_EMBED=..." \
  --platform <cpu_platform> --preset <cpu_preset>
```

- **Compute.** No GPU is needed; inference happens on Token Factory. Pick a CPU platform and preset from
  [VM types](https://docs.nebius.com/compute/virtual-machines/types); the two flags must match.
- **Auth.** The command above leaves `--auth` off, because the browser calls the API directly and a bearer token in
  frontend code would be public anyway. Add `--auth token` if the API is only called server-side.
- **URL.** Creation takes about 5 minutes. Get the HTTPS URL with:

```bash
nebius ai endpoint list
nebius ai endpoint get <endpoint_ID> --format json | jq -r '.status.public_endpoints[] | select(startswith("https://"))' | head -1
```

- **Background jobs.** Cases run as FastAPI background tasks inside the container. Keep the endpoint running while a
  case processes. Uploaded files sit on the container's disk only until the case is deleted or the container restarts.
- **Database.** Create a Managed PostgreSQL cluster and use its connection string as `DATABASE_URL`
  (`postgresql+psycopg://user:pass@host:5432/db`). Tables and the `vector` extension are created on startup.

### Frontend → Vercel

Import the repo in Vercel with **Root Directory** `frontend` and set `NEXT_PUBLIC_API_URL` to the endpoint's HTTPS URL.

## Privacy and safety

- Policy numbers are masked to the last 4 digits in code before they are stored or shown.
- Prompts, responses and document text are never written to logs.
- **Delete case and files** removes the uploads and every database row for the case (documents, clauses, sources,
  model-call logs).
- Use synthetic or redacted documents for demos. `.env` and real documents must never be committed.

## Licence

MIT. See [LICENSE](LICENSE).
