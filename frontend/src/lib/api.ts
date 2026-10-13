export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Outcome = "contestable" | "likely_valid" | "unclear";
export type Issue = { kind: "clause" | "date" | "url" | "clause_id" | "source_id"; value: string };
export type Clause = { id: number; clause_no: string; tag: string; text: string };
export type Cost = { calls: number; input_tokens: number; output_tokens: number; usd: number };
export type TrackerStep = { stage: string; filed_on: string | null; opens_on: string | null; open: boolean };
export type PackKey = "grievance" | "bima_bharosa" | "ombudsman";

export type CaseResult = {
  case_id: string;
  documents: Record<string, string>;
  rejection: {
    insurer: string;
    claim_no: string;
    policy_no_masked: string;
    policy_start_date: string | null;
    rejection_date: string;
    reason_text: string;
    cited_clauses: string[];
    reason_type: string;
  };
  facts: {
    diagnosis: string;
    admission_date: string;
    discharge_date: string;
    history_mentioned: string[];
    procedures: string[];
  };
  dates: {
    policy_start: string;
    admission_date: string;
    days_policy_to_admission: number;
    coverage_full_years: number;
    waiting_period: string | null;
    waiting_period_ends: string | null;
    waiting_period_over: boolean | null;
    history_onsets: Record<string, string | null>;
    history_onset_before_policy: Record<string, boolean | null>;
  };
  clauses: Clause[];
  sources: { id: number; title: string; url: string }[];
  verdict: {
    outcome: Outcome;
    confidence: "low" | "medium" | "high";
    reasons: string[];
    clause_ids: number[];
    source_ids: number[];
    missing_documents: string[];
  };
  pack: Record<PackKey, string> | null;
  no_pack_reason: string | null;
  issues: Record<string, Issue[]>;
};

export type CaseView = {
  id: string;
  created_at: string;
  status: "processing" | "done" | "error";
  stage: string | null;
  error: string | null;
  result: CaseResult | null;
  documents: { filename: string; doc_type: string }[];
  cost: Cost;
  tracker: TrackerStep[];
};

export type CaseSummary = {
  id: string;
  created_at: string;
  status: CaseView["status"];
  claim_no: string | null;
  insurer: string | null;
  outcome: Outcome | null;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API + path, init);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${r.status})`);
  }
  return (r.status === 204 ? undefined : r.json()) as T;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  listCases: () => call<CaseSummary[]>("/cases"),
  getCase: (id: string) => call<CaseView>(`/cases/${id}`),
  createCase: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return call<{ id: string }>("/cases", { method: "POST", body: form });
  },
  deleteCase: (id: string) => call<void>(`/cases/${id}`, { method: "DELETE" }),
  getClause: (id: string, no: string) => call<Clause>(`/cases/${id}/clauses/${encodeURIComponent(no)}`),
  verify: (id: string, text: string) => call<Issue[]>(`/cases/${id}/verify`, json("POST", { text })),
  setTracker: (id: string, stage: string, filed_on: string | null) =>
    call<TrackerStep[]>(`/cases/${id}/tracker`, json("PUT", { stage, filed_on })),
};

export const DOC_LABEL: Record<string, string> = {
  rejection_letter: "Rejection letter",
  policy: "Policy wording",
  discharge_summary: "Discharge summary",
  bill: "Bill",
  other: "Other",
};

export const OUTCOME_LABEL: Record<Outcome, string> = {
  contestable: "Contestable",
  likely_valid: "Likely valid",
  unclear: "Unclear",
};

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso + (iso.length === 10 ? "T00:00:00" : "")).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
