# Submission kit

Draft Devpost text and a video script. Replace every `[[...]]` before submitting. Numbers come from
[results.md](results.md); re-run `python ../scripts/measure.py` from `backend/` after switching to Token Factory.

## Checklist

- [ ] `.env` points at Token Factory (`NEBIUS_BASE_URL`, model IDs from the catalog); `python scripts/smoke_models.py` passes
- [ ] `docs/results.md` regenerated on Token Factory; README "Results" table and cost line updated to match
- [ ] README TODOs filled: Token Factory experience, Nebius services actually used
- [ ] Backend live on a Nebius Serverless endpoint; frontend on Vercel; the public URL opens on a phone
- [ ] Sample A runs end to end on the public URL
- [ ] Video recorded (under 3 minutes unless the rules say otherwise) and uploaded
- [ ] Devpost form filled; repo link https://github.com/lahari936/claim-back; licence MIT
- [ ] Submitted by the night of 29 Oct (deadline 30 Oct 2026, 10:30 pm IST)

---

## Devpost

**Name:** ClaimBack

**Tagline:** Was your health claim rejected fairly? ClaimBack checks the insurer's reason against your own policy and drafts the appeal.

### Inspiration

When an Indian health insurer rejects a claim, the letter usually cites a clause number and a phrase like
"pre-existing disease" or "waiting period". Checking it means reading the policy wording, finding the definitions,
working out dates from the policy start, and knowing the escalation path: insurer grievance, then Bima Bharosa,
then the Insurance Ombudsman. Most families don't do this, and some valid claims stay rejected.
[[Add a personal line if you have one.]]

### What it does

- Upload the rejection letter, the policy wording and the discharge summary, as PDFs or phone photos. Each file is
  labelled automatically.
- ClaimBack extracts the stated reason and cited clauses, indexes the policy clause by clause, and pulls the cited
  clause plus the definitions it depends on.
- It works out the dates in code: when the waiting period ended, how long the policy had run, and when a condition
  in the medical history began compared with the policy start.
- It searches IRDAI, Bima Bharosa and Ombudsman sites live with Tavily.
- Nemotron Ultra gives a verdict: contestable, likely valid or unclear, with reasons tied to clauses and facts.
- If it is worth contesting, it drafts a grievance letter, a Bima Bharosa complaint and an Ombudsman complaint.
- A verifier checks every clause number, date and URL in the drafts against the policy index, the computed dates
  and the stored sources. Anything unverified is shown in red, including after you edit a draft.
- A tracker shows when each escalation stage opens, and every case shows its own model cost.

### How we built it

- **Models:** Nemotron on Nebius Token Factory, routed by step. Nano Omni reads photos and scans; Nano 30B-A3B
  classifies and extracts; Super 120B writes research queries; Ultra 550B gives the verdict and drafts; Nemotron
  Embed powers clause search.
- **Backend:** Python, FastAPI and Pydantic; every model output is schema-validated with one retry.
- **Data:** PostgreSQL with pgvector for the clause index; Tavily for regulator sources.
- **Frontend:** Next.js, Tailwind and shadcn/ui.
- **Deploy:** backend container on Nebius Serverless AI endpoints, frontend on Vercel.

### Challenges

- **Reasoning-model output.** Answers come in `content` with the thinking in a separate field; the client handles both.
- **Vision loops.** With thinking on, the vision model looped on a full-page transcription. Turning thinking off
  gave an exact transcription.
- **Keeping the model honest.** Dates are computed in code, clauses are split in code so their wording stays exact,
  and drafts may only cite clause numbers, dates and URLs we can check.

### Accomplishments

- [[from results.md]] correct verdicts on the synthetic cases, including a genuine waiting-period exclusion where
  ClaimBack says the insurer is right and drafts nothing.
- Zero unverified clauses, dates or links in the generated drafts on the fixtures.
- About [[N]] model calls and [[$X]] per case.

### What we learned

Mix code and models. LLMs read messy documents and write well; code does the date maths and the checking. Making
"likely valid" a first-class outcome matters as much as finding contestable cases.

### What's next

- Partial deductions (room-rent capping, proportionate deductions)
- Hindi and other regional-language output
- Reading the policy schedule for the exact start date and renewals
- Ombudsman award search to cite precedent

**Built with:** nemotron, nebius-token-factory, nebius-serverless, tavily, python, fastapi, pydantic, postgresql,
pgvector, pymupdf, next.js, typescript, tailwindcss, shadcn-ui, vercel

---

## Video script (about 2:45)

| Time | Screen | Voice-over |
| --- | --- | --- |
| 0:00–0:15 | A rejection letter (sample A) | "This health claim was rejected for a 'pre-existing disease'. Is that fair? Most people can't tell. ClaimBack can." |
| 0:15–0:35 | Home page; click sample A; files listed; Check my claim | "Upload the rejection letter, the policy and the discharge summary, as PDFs or phone photos." |
| 0:35–0:55 | Progress view: steps ticking, documents auto-labelled, live cost | "Nemotron models on Nebius Token Factory read and label each document. Small models do extraction; the big one only weighs the verdict." |
| 0:55–1:25 | Verdict card: Contestable, high; click "clause 1.1" to open the clause | "The verdict: contestable. The policy defines pre-existing as diagnosed before the policy started. The diabetes began about a year before this admission, years after the policy started. Every clause opens in place." |
| 1:25–1:45 | Reason vs policy, then Computed dates | "Insurer's words on the left, the policy on the right. The dates are worked out in code, not by the AI, so they can't be invented." |
| 1:45–2:10 | Escalation pack tabs; Edit; type a fake clause such as 9.9; Done; it turns red | "If it's worth fighting, you get a grievance letter, a Bima Bharosa complaint and an Ombudsman draft. Every clause, date and link is checked. Add something unsupported and it's flagged." |
| 2:10–2:25 | Case C: Likely valid, no pack drafted | "And when the insurer is right, ClaimBack says so. Here the waiting period really hadn't ended, so no appeal is drafted." |
| 2:25–2:35 | Tracker and the cost panel | "A tracker shows when each escalation opens. Each case costs about [[$X]] in model calls." |
| 2:35–2:45 | Architecture slide or README diagram; repo URL | "Nemotron on Token Factory, Nebius Serverless, Tavily for live regulator sources. ClaimBack: get your claim back." |

Tips: record at 1280×800 or above; run the cases before recording and open them from "Your cases" so there is no
5-minute wait on camera; show the progress view from a run you started earlier.
