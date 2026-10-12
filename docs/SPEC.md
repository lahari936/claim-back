# ClaimBack — Health Claim Appeal Agent: Implementation Spec

Hackathon: Nebius x NVIDIA Global AI Hackathon · Track: Best Apps and Agents (+ Best Use of Tavily)
Deadline: 30 Oct 2026, 10:30 pm IST

ClaimBack turns a rejection letter, the policy wording and hospital papers into a verdict plus an escalation pack (insurer grievance → Bima Bharosa → Insurance Ombudsman).
Hackathon scope: full rejections for four common reasons — pre-existing disease, waiting period, non-disclosure, "not medically necessary". Partial deductions are out of scope.

---

## 1. How to use this with Claude Code

1. Save this file in an empty repo as `docs/SPEC.md`.
2. Create `CLAUDE.md` at the repo root with the block below.
3. Run Claude Code phase by phase using the prompts in section 11. Review and commit after each phase.

```markdown
# CLAUDE.md
Read docs/SPEC.md before any task. Project: ClaimBack (Health Claim Appeal Agent).
Rules:
- All LLM calls go through backend/app/llm/client.py; never call the API directly elsewhere.
- Date maths happens in Python, never in an LLM prompt.
- Every citation in generated text must come from a Tavily result stored in the sources table.
- Every clause number quoted must exist in the policy clause index.
- Pydantic models for every LLM output; validate and retry once on failure.
- Mask policy numbers and patient names in logs.
- Write tests with each module. Run `pytest` before saying a phase is done.
- Never commit .env or real documents. Sample files go in /samples and must be synthetic.
```

---

## 2. Stack

| Layer | Choice | Why |
| --- | --- | --- |
| LLM | Nemotron on Nebius Token Factory (OpenAI-compatible API) | Hackathon requirement |
| Web research | Tavily Search API | Live regulator sources; Tavily prize |
| Backend | Python 3.12, FastAPI, Pydantic v2 | Typed LLM outputs |
| Document input | PyMuPDF for digital PDFs; Nemotron 3 Nano Omni for scans/photos | No separate OCR service |
| Database | PostgreSQL + pgvector | Cases plus policy clause search |
| Embeddings | An embedding model from the Token Factory catalog (prefer an NVIDIA one if listed) | Clause retrieval |
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui | Polished UI for the Design score |
| Deploy | Backend container on Nebius Serverless Endpoints; frontend on Vercel | Shows Nebius beyond Token Factory |

## 3. Model routing

Check these IDs against your Token Factory catalog before coding; the catalog changes.

| Tier | Step | Model ID |
| --- | --- | --- |
| vision | Read scanned letters, bills, discharge summaries | `nvidia/Nemotron-3-Nano-Omni` (confirm image input) |
| fast | Classify documents, split/tag clauses, extract facts, verify | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| agent | Clause retrieval, research tool calls | `nvidia/nemotron-3-super-120b-a12b` |
| reason | Verdict and escalation drafts | `nvidia/Nemotron-3-Ultra-550b-a55b` |

**Known catch:** Nemotron models on Token Factory are reasoning models. Clients that read only `message.content` can get empty output (reported in a Nebius GitHub issue, May 2026). Log the raw response on day 1 and handle both fields.

## 4. Shared code

### LLM client (the only place that calls the API)

```python
# backend/app/llm/client.py
import os
from openai import OpenAI
from pydantic import BaseModel, ValidationError

client = OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])

MODELS = {
    "vision": os.environ["MODEL_VISION"],
    "fast": os.environ["MODEL_FAST"],
    "agent": os.environ["MODEL_AGENT"],
    "reason": os.environ["MODEL_REASON"],
}

def _text(msg) -> str:
    # Reasoning models may leave content empty; fall back to the reasoning field.
    return msg.content or getattr(msg, "reasoning_content", None) or ""

def call_json(tier: str, system: str, user: str, schema: type[BaseModel], case_id: str):
    for _ in range(2):
        r = client.chat.completions.create(
            model=MODELS[tier],
            messages=[{"role": "system", "content": system + "\nReturn only JSON matching the schema."},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        log_usage(case_id, tier, r.usage)  # writes tokens and cost to llm_calls
        try:
            return schema.model_validate_json(_text(r.choices[0].message))
        except ValidationError as e:
            user += f"\n\nYour last output failed validation: {e}. Fix it."
    raise RuntimeError("LLM output invalid after retry")
```

The `llm_calls` table (case_id, tier, model, input_tokens, output_tokens, cost) feeds a "cost per case" panel. Show it in the video.

### Research helper

```python
# backend/app/research/tavily.py
import os
from tavily import TavilyClient
tv = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

INSURANCE_DOMAINS = ["irdai.gov.in", "bimabharosa.irdai.gov.in", "cioins.co.in"]

def search_official(query: str, domains: list[str] = INSURANCE_DOMAINS) -> list[dict]:
    res = tv.search(query=query, include_domains=domains, search_depth="advanced", max_results=5)
    return [{"title": r["title"], "url": r["url"], "content": r["content"]} for r in res["results"]]
```

Store every result in the `sources` table linked to the case. Drafts may cite only rows from that table.

### Repo layout

```
repo/
  CLAUDE.md  LICENSE (MIT)  README.md  docker-compose.yml  .env.example
  docs/SPEC.md
  backend/app/
    main.py            # FastAPI routes
    llm/client.py
    research/tavily.py
    pipeline/          # ingest, classify, extract, retrieve, research, verdict, draft, verify
    domain/            # policy.py (clause index), dates.py
    models.py          # Pydantic + SQLAlchemy
  backend/tests/
  frontend/            # Next.js app
  samples/claimback/   # synthetic demo files only
```

### Environment variables

`NEBIUS_BASE_URL`, `NEBIUS_API_KEY`, `MODEL_VISION`, `MODEL_FAST`, `MODEL_AGENT`, `MODEL_REASON`, `MODEL_EMBED`, `TAVILY_API_KEY`, `DATABASE_URL`, `NEXT_PUBLIC_API_URL`.

Base URL: use the one in your Nebius console (e.g. `https://api.tokenfactory.nebius.com/v1/` or `https://api.tokenfactory.us-central1.nebius.com/v1/`).

---

## 5. Pipeline

1. **Ingest** (`pipeline/ingest.py`): digital PDF → PyMuPDF text. Scan or photo → Nano Omni transcription.
2. **Classify documents** (fast): label each file as rejection letter, policy, discharge summary, bill or other.
3. **Extract rejection** (fast): letter → `Rejection` schema.
4. **Index policy** (`domain/policy.py`, fast + embeddings): split the policy into clauses with their numbers; tag each as definition, exclusion, waiting_period, sub_limit, procedure or other. Store in pgvector.
5. **Extract medical facts** (fast): discharge summary → `MedicalFacts`.
6. **Compute dates** (`domain/dates.py`, code only): policy start, continuous-coverage years, days between policy start and admission, waiting-period status for the cited exclusion.
7. **Retrieve clauses** (agent): the cited clause plus its definitions (e.g. the policy's own definition of "pre-existing disease").
8. **Research** (agent + Tavily): regulator guidance on the rejection type.
9. **Verdict** (reason): `Verdict` schema. Weigh facts and computed dates against the clause wording; say which side is stronger.
10. **Draft pack** (reason): grievance letter to the insurer's GRO; Bima Bharosa complaint text; Ombudsman complaint draft. Only if the verdict is "contestable" or "unclear".
11. **Verify** (code + fast): every clause number quoted must exist in the index; every date must match computed dates; every URL must be in `sources`. Failures highlighted red.

## 6. Data schemas

```python
from datetime import date
from typing import Literal
from pydantic import BaseModel

class Rejection(BaseModel):
    insurer: str
    claim_no: str
    policy_no_masked: str        # keep last 4 only
    rejection_date: date
    reason_text: str             # verbatim
    cited_clauses: list[str]     # e.g. ["4.1", "Exclusion 3"]
    reason_type: Literal["pre_existing", "waiting_period", "non_disclosure",
                         "not_medically_necessary", "other"]

class MedicalFacts(BaseModel):
    diagnosis: str
    admission_date: date
    discharge_date: date
    history_mentioned: list[str]   # verbatim phrases, e.g. "k/c/o HTN 2 yrs"
    procedures: list[str]

class Clause(BaseModel):
    clause_no: str
    text: str
    tag: Literal["definition", "exclusion", "waiting_period", "sub_limit", "procedure", "other"]

class Verdict(BaseModel):
    outcome: Literal["contestable", "likely_valid", "unclear"]
    confidence: Literal["low", "medium", "high"]
    reasons: list[str]          # each must cite a clause id or a fact
    clause_ids: list[int]
    source_ids: list[int]
    missing_documents: list[str]
```

## 7. Prompts (starting points)

- **Clause split (fast):** "Split this policy text into numbered clauses. Keep each clause's number and full wording. Tag each clause with one of: definition, exclusion, waiting_period, sub_limit, procedure, other."
- **Verdict (reason):** "You are reviewing an insurer's claim rejection for the policyholder. Using only the clauses, medical facts and computed dates given, decide whether the stated reason holds. Quote clause numbers. If the facts support the insurer, say so plainly. Do not give medical advice."
- **Grievance (reason):** "Write a firm, polite grievance letter to the insurer's Grievance Redressal Officer. State the claim number, the stated reason, why it does not apply (citing clauses and facts), and the relief sought. Under 400 words."

## 8. UI screens

1. **New case:** drag-and-drop several files; auto-labelled by type.
2. **Reason vs policy:** rejection reason left; cited clause and its definitions right; computed dates beneath.
3. **Verdict card:** outcome, confidence, reasons with links, missing documents.
4. **Escalation pack:** three tabs (Insurer, Bima Bharosa, Ombudsman) with editable drafts and export.
5. **Tracker:** stage, date filed, when the next stage opens.

Banner on every draft: "Draft for your review. Not legal or medical advice." Nothing is filed automatically. One-click delete for each case.

## 9. Test fixtures

Create 4 synthetic cases in `/samples/claimback/` with invented names and a made-up policy wording (do not copy a real insurer's policy):

- **Case A:** "pre-existing" rejection where the history began after the policy start → contestable.
- **Case B:** waiting-period rejection where the waiting period had in fact ended → contestable.
- **Case C:** genuine waiting-period exclusion → likely_valid; no pack drafted.
- **Case D:** scanned discharge summary photo, to show Nano Omni.

## 10. Acceptance criteria

- [ ] Correct verdict on cases A–C
- [ ] Case C produces no appeal pack, with a clear reason
- [ ] Every clause number in drafts exists in the policy index
- [ ] Dates in drafts match `domain/dates.py` output
- [ ] Policy numbers masked in logs and the UI
- [ ] One-click delete removes the case's files and rows
- [ ] Cost per case shown in the UI

---

## 11. Build plan (Oct 12–30) with Claude Code prompts

Feature work stops on 27 Oct. Don't start a phase until the previous gate passes.

1. **Setup + model check (Oct 12–13).** Claim Nebius Builder Program credits; get Nebius and Tavily keys.
   - Prompt: "Read docs/SPEC.md. Scaffold the repo exactly as in 'Repo layout': docker-compose with Postgres + pgvector, FastAPI health route, Next.js app, .env.example, MIT LICENSE. Then write scripts/smoke_models.py that calls each MODEL_* env var (including the embedding model) with a one-line input and prints the content and any reasoning field."
   - Gate: all models respond and you know which field holds the answer.
2. **Core pipeline (Oct 14–18).**
   - Prompt: "Create the synthetic fixtures in section 9, including a made-up policy PDF. Then implement llm/client.py with the llm_calls table, pipeline/ingest.py, classify and extract steps, domain/policy.py with pgvector clause index, and domain/dates.py, with pytest tests against the fixtures."
   - Gate: extraction, clause indexing and date tests pass on every fixture.
3. **Reasoning + verify (Oct 19–22).**
   - Prompt: "Implement research/tavily.py with a sources table, then retrieve, research, verdict, draft and verify steps in spec order. Add a test that plants a fake clause number, a wrong date and a fake URL in a draft and asserts the verifier flags all three."
   - Gate: one full case runs end to end from the command line, and case C gets no pack.
4. **Frontend (Oct 21–25).**
   - Prompt: "Build the UI screens in section 8 with Next.js, Tailwind and shadcn/ui. Wire them to the FastAPI routes. Unverified claims show red; clause citations open the clause; add the cost-per-case panel and one-click delete."
   - Gate: a case runs fully through the browser.
5. **Deploy + polish (Oct 26–27).**
   - Prompt: "Containerise the backend and document deployment to Nebius Serverless Endpoints in the README. Write the README sections the hackathon requires: setup, running, Nemotron models used, where Token Factory helped, other Nebius services used."
   - Gate: the public URL works from a phone. If behind schedule, cut the tracker and Ombudsman tab first.
6. **Video, README, submit (Oct 28–29).** Measure results on the fixtures, record the video, fill in the Devpost placeholders, submit by the night of 29 Oct. 30 Oct is buffer.

## 12. Risks and guardrails

| Risk | Guardrail |
| --- | --- |
| Made-up clause or regulation | Drafts cite only indexed clause ids and stored source ids; verifier rejects anything else |
| Wrong dates | All date maths in code; verifier matches every date |
| Overstating a weak case | Verdict can be "likely_valid"; no pack drafted then |
| Reads as legal/medical advice | Banner on every draft; nothing filed automatically |
| Real patient data | Synthetic samples only; masked IDs; one-click delete |
| Reasoning-model output parsing | Handle empty `content`; log raw responses in week 1 |
| Ultra latency / credits | Ultra only for verdict and drafts; cache per case; budget alert |
| Model IDs change | IDs in env vars, not code |
| Running out of time | Pre-decided cuts: tracker, Ombudsman tab, multilingual output |
