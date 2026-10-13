"use client";

import { LinkedText } from "@/components/linked-text";
import { OutcomeBadge } from "@/components/outcome-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  DOC_LABEL,
  fmtDate,
  type CaseResult,
  type CaseView,
  type Clause,
  type Cost,
  type Issue,
  type PackKey,
  type TrackerStep,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  Check,
  CircleDashed,
  Copy,
  Download,
  ExternalLink,
  Loader2,
  Pencil,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const STEPS = [
  "Reading",
  "Extracting rejection and medical facts",
  "Indexing policy clauses",
  "Retrieving clauses and computing dates",
  "Researching IRDAI guidance",
  "Weighing the verdict",
  "Drafting escalation pack",
  "Verifying citations and dates",
];

const PACK_TABS: { key: PackKey; label: string; hint: string }[] = [
  { key: "grievance", label: "Insurer", hint: "Send to the insurer's Grievance Redressal Officer first." },
  { key: "bima_bharosa", label: "Bima Bharosa", hint: "Use on bimabharosa.irdai.gov.in if the insurer doesn't resolve it in 14 days." },
  { key: "ombudsman", label: "Ombudsman", hint: "File with the Insurance Ombudsman if the insurer rejects or doesn't reply within 30 days." },
];

const STAGE_LABEL: Record<string, string> = {
  grievance: "Grievance to insurer",
  bima_bharosa: "Bima Bharosa complaint",
  ombudsman: "Insurance Ombudsman",
};

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [view, setView] = useState<CaseView | null>(null);
  const [missing, setMissing] = useState(false);
  const [clauseNo, setClauseNo] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const v = await api.getCase(id);
        setView(v);
        if (v.status === "processing") timer = setTimeout(poll, 3000);
      } catch {
        setMissing(true);
      }
    };
    poll();
    return () => clearTimeout(timer);
  }, [id]);

  const remove = async () => {
    if (!confirm("Delete this case, its files and all drafts? This cannot be undone.")) return;
    await api.deleteCase(id);
    router.push("/");
  };

  if (missing) return <p className="text-muted-foreground">This case doesn&apos;t exist or was deleted.</p>;
  if (!view) return <Loader2 className="text-muted-foreground animate-spin" />;

  return (
    <div className="space-y-8">
      {view.status === "processing" && <Processing view={view} />}
      {view.status === "error" && (
        <Card className="border-flag/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="text-flag size-5" /> We couldn&apos;t finish this case
            </CardTitle>
            <CardDescription>{view.error}</CardDescription>
          </CardHeader>
        </Card>
      )}
      {view.status === "done" && view.result && (
        <Result caseId={id} r={view.result} cost={view.cost} tracker={view.tracker} onClause={setClauseNo} />
      )}

      <div className="flex justify-end">
        <Button variant="outline" onClick={remove} className="text-destructive">
          <Trash2 /> Delete case and files
        </Button>
      </div>

      <ClauseDialog caseId={id} clauseNo={clauseNo} onClose={() => setClauseNo(null)} />
    </div>
  );
}

function Processing({ view }: { view: CaseView }) {
  const current = Math.max(0, STEPS.findIndex((s) => view.stage?.startsWith(s)));
  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="font-serif text-2xl">Reading your claim</CardTitle>
          <CardDescription>This takes a few minutes. You can leave this page and come back.</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3">
            {STEPS.map((s, i) => (
              <li key={s} className={cn("flex items-center gap-3 text-sm", i > current && "text-muted-foreground")}>
                {i < current ? (
                  <Check className="text-contestable size-4" />
                ) : i === current ? (
                  <Loader2 className="text-primary size-4 animate-spin" />
                ) : (
                  <CircleDashed className="size-4" />
                )}
                {i === current && view.stage ? view.stage : s}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {view.documents.length === 0 ? (
              <p className="text-muted-foreground text-sm">Labelling files…</p>
            ) : (
              <ul className="space-y-2">
                {view.documents.map((d) => (
                  <li key={d.filename} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">{d.filename}</span>
                    <Badge variant="secondary">{DOC_LABEL[d.doc_type] ?? d.doc_type}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <CostPanel cost={view.cost} live />
      </div>
    </div>
  );
}

function Result({
  caseId,
  r,
  cost,
  tracker,
  onClause,
}: {
  caseId: string;
  r: CaseResult;
  cost: Cost;
  tracker: TrackerStep[];
  onClause: (no: string) => void;
}) {
  const v = r.verdict;
  const verdictIssues = r.issues.verdict ?? [];
  const cited = new Set(r.rejection.cited_clauses);
  return (
    <>
      <div className="space-y-1">
        <p className="text-muted-foreground text-sm">
          {r.rejection.insurer} · Claim {r.rejection.claim_no} · Policy {r.rejection.policy_no_masked}
        </p>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">
          {r.facts.diagnosis} <span className="text-muted-foreground font-normal">rejected on {fmtDate(r.rejection.rejection_date)}</span>
        </h1>
      </div>

      {/* Verdict */}
      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card
          className={cn(
            "border-l-4",
            v.outcome === "contestable" && "border-l-contestable",
            v.outcome === "unclear" && "border-l-unclear",
            v.outcome === "likely_valid" && "border-l-valid",
          )}
        >
          <CardHeader>
            <div className="flex flex-wrap items-center gap-3">
              <OutcomeBadge outcome={v.outcome} className="px-3 py-1 text-sm" />
              <span className="text-muted-foreground text-sm">{v.confidence} confidence</span>
            </div>
            <CardTitle className="font-serif text-2xl leading-snug">
              {v.outcome === "contestable"
                ? "The insurer's reason looks weak against your policy."
                : v.outcome === "likely_valid"
                  ? "The insurer's reason appears to hold."
                  : "The documents don't settle it either way."}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <ol className="list-decimal space-y-3 pl-5 leading-relaxed">
              {v.reasons.map((reason, i) => (
                <li key={i}>
                  <LinkedText text={reason} issues={verdictIssues} onClause={onClause} />
                </li>
              ))}
            </ol>
            {verdictIssues.length > 0 && <IssueNote issues={verdictIssues} />}
            {v.missing_documents.length > 0 && (
              <div>
                <p className="mb-1 text-sm font-medium">Documents that would strengthen this</p>
                <ul className="text-muted-foreground list-disc space-y-1 pl-5 text-sm">
                  {v.missing_documents.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
        <div className="space-y-6">
          <CostPanel cost={cost} />
          <Card>
            <CardHeader>
              <CardTitle>Regulator sources</CardTitle>
              <CardDescription>Found live with Tavily. Drafts may cite only these.</CardDescription>
            </CardHeader>
            <CardContent>
              {r.sources.length === 0 ? (
                <p className="text-muted-foreground text-sm">None found.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {r.sources.map((s) => (
                    <li key={s.id} className="flex gap-2">
                      <ExternalLink className="text-muted-foreground mt-0.5 size-3.5 shrink-0" />
                      <a href={s.url} target="_blank" rel="noreferrer" className="line-clamp-2 hover:underline">
                        {s.title}
                      </a>
                      {v.source_ids.includes(s.id) && (
                        <Badge variant="secondary" className="ml-auto">
                          cited
                        </Badge>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Reason vs policy */}
      <section className="space-y-4">
        <h2 className="font-serif text-2xl font-semibold">Reason vs policy</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardDescription>What the insurer said</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <blockquote className="border-primary/40 font-serif text-lg leading-relaxed italic border-l-2 pl-4">
                “{r.rejection.reason_text}”
              </blockquote>
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="text-muted-foreground">Cites</span>
                {r.rejection.cited_clauses.map((c) => (
                  <button key={c} type="button" className="clause-link" onClick={() => onClause(c)}>
                    clause {c}
                  </button>
                ))}
              </div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 border-t pt-4 text-sm">
                <dt className="text-muted-foreground">Diagnosis</dt>
                <dd>{r.facts.diagnosis}</dd>
                <dt className="text-muted-foreground">History noted</dt>
                <dd>{r.facts.history_mentioned.length ? r.facts.history_mentioned.join("; ") : "None recorded"}</dd>
                <dt className="text-muted-foreground">Procedures</dt>
                <dd>{r.facts.procedures.length ? r.facts.procedures.join("; ") : "None"}</dd>
              </dl>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>What the policy says</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {r.clauses.map((c) => (
                <div
                  key={c.id}
                  className={cn("rounded-lg border p-3", cited.has(c.clause_no) && "border-primary/50 bg-accent/40")}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span className="font-semibold">{c.clause_no}</span>
                    <Badge variant="outline" className="capitalize">
                      {c.tag.replace("_", " ")}
                    </Badge>
                    {cited.has(c.clause_no) && <Badge>cited by insurer</Badge>}
                  </div>
                  <p className="text-sm leading-relaxed">{c.text}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
        <DatesPanel r={r} />
      </section>

      {/* Escalation pack */}
      <section className="space-y-4">
        <h2 className="font-serif text-2xl font-semibold">Escalation pack</h2>
        {r.pack ? (
          <Pack caseId={caseId} pack={r.pack} issues={r.issues} onClause={onClause} />
        ) : (
          <Card>
            <CardContent className="flex items-start gap-3">
              <ShieldCheck className="text-valid mt-0.5 size-5 shrink-0" />
              <div className="space-y-1">
                <p className="font-medium">No appeal drafted</p>
                <p className="text-muted-foreground text-sm">{r.no_pack_reason}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </section>

      {r.pack && <Tracker caseId={caseId} initial={tracker} />}
    </>
  );
}

function DatesPanel({ r }: { r: CaseResult }) {
  const d = r.dates;
  const rows: [string, string][] = [
    ["Policy start", fmtDate(d.policy_start)],
    ["Admission", fmtDate(d.admission_date)],
    ["Days covered before admission", `${d.days_policy_to_admission} (${d.coverage_full_years} full years)`],
  ];
  if (d.waiting_period)
    rows.push([
      `Waiting period (${d.waiting_period})`,
      `${d.waiting_period_over ? "Ended" : "Runs until"} ${fmtDate(d.waiting_period_ends)}`,
    ]);
  for (const [h, onset] of Object.entries(d.history_onsets))
    rows.push([
      `“${h}” began around`,
      onset ? `${fmtDate(onset)} · ${d.history_onset_before_policy[h] ? "before" : "after"} policy start` : "No duration given",
    ]);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Computed dates</CardTitle>
        <CardDescription>Worked out in code from your documents, not by the AI.</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map(([k, val]) => (
            <div key={k}>
              <dt className="text-muted-foreground text-xs">{k}</dt>
              <dd className="font-medium">{val}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function Pack({
  caseId,
  pack,
  issues,
  onClause,
}: {
  caseId: string;
  pack: Record<PackKey, string>;
  issues: Record<string, Issue[]>;
  onClause: (no: string) => void;
}) {
  return (
    <Card>
      <CardContent className="space-y-4">
        <div className="bg-unclear-soft text-foreground flex items-start gap-2 rounded-lg px-3 py-2 text-sm">
          <AlertTriangle className="text-unclear mt-0.5 size-4 shrink-0" />
          Draft for your review. Not legal or medical advice. Nothing is filed automatically.
        </div>
        <Tabs defaultValue="grievance">
          <TabsList>
            {PACK_TABS.map((t) => (
              <TabsTrigger key={t.key} value={t.key}>
                {t.label}
                {(issues[t.key]?.length ?? 0) > 0 && <span className="bg-flag size-1.5 rounded-full" />}
              </TabsTrigger>
            ))}
          </TabsList>
          {PACK_TABS.map((t) => (
            <TabsContent key={t.key} value={t.key}>
              <Draft caseId={caseId} name={t.key} hint={t.hint} initial={pack[t.key]} initialIssues={issues[t.key] ?? []} onClause={onClause} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}

function Draft({
  caseId,
  name,
  hint,
  initial,
  initialIssues,
  onClause,
}: {
  caseId: string;
  name: string;
  hint: string;
  initial: string;
  initialIssues: Issue[];
  onClause: (no: string) => void;
}) {
  const [text, setText] = useState(initial);
  const [issues, setIssues] = useState(initialIssues);
  const [editing, setEditing] = useState(false);
  const [checking, setChecking] = useState(false);
  const [copied, setCopied] = useState(false);

  const finishEdit = async () => {
    setEditing(false);
    setChecking(true);
    try {
      setIssues(await api.verify(caseId, text));
    } finally {
      setChecking(false);
    }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    Object.assign(document.createElement("a"), { href: url, download: `claimback-${name}.txt` }).click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">{hint}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => (editing ? finishEdit() : setEditing(true))}>
            {editing ? <Check /> : <Pencil />} {editing ? "Done" : "Edit"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              await navigator.clipboard.writeText(text);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
          >
            <Copy /> {copied ? "Copied" : "Copy"}
          </Button>
          <Button variant="outline" size="sm" onClick={download}>
            <Download /> .txt
          </Button>
        </div>
      </div>
      {editing ? (
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="min-h-96 font-serif text-base leading-relaxed"
          autoFocus
        />
      ) : (
        <div className="bg-background rounded-lg border px-5 py-4 font-serif leading-relaxed whitespace-pre-wrap sm:px-8 sm:py-6">
          <LinkedText text={text} issues={issues} onClause={onClause} />
        </div>
      )}
      {checking ? (
        <p className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="size-4 animate-spin" /> Re-checking clauses, dates and links…
        </p>
      ) : issues.length > 0 ? (
        <IssueNote issues={issues} />
      ) : (
        <p className="text-contestable flex items-center gap-2 text-sm">
          <ShieldCheck className="size-4" /> Every clause, date and link checks out against your documents.
        </p>
      )}
    </div>
  );
}

function IssueNote({ issues }: { issues: Issue[] }) {
  const what: Record<Issue["kind"], string> = {
    clause: "clause not in your policy",
    date: "date not in your documents",
    url: "link not from the stored sources",
    clause_id: "unknown clause reference",
    source_id: "unknown source reference",
  };
  return (
    <div className="border-flag/40 bg-flag-soft rounded-lg border px-3 py-2 text-sm">
      <p className="text-flag font-medium">Check before using — {issues.length} item(s) couldn&apos;t be verified:</p>
      <ul className="mt-1 list-disc pl-5">
        {issues.map((i, k) => (
          <li key={k}>
            <span className="font-mono text-xs">{i.value}</span> — {what[i.kind]}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Tracker({ caseId, initial }: { caseId: string; initial: TrackerStep[] }) {
  const [steps, setSteps] = useState(initial);
  return (
    <section className="space-y-4">
      <h2 className="font-serif text-2xl font-semibold">Tracker</h2>
      <ol className="grid gap-4 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={s.stage} className={cn("bg-card rounded-xl border p-4", s.filed_on && "border-contestable/50")}>
            <p className="text-muted-foreground text-xs">Stage {i + 1}</p>
            <p className="font-medium">{STAGE_LABEL[s.stage] ?? s.stage}</p>
            <p className="text-muted-foreground mt-1 text-sm">
              {s.filed_on
                ? `Filed ${fmtDate(s.filed_on)}`
                : s.opens_on
                  ? s.open
                    ? "Open now"
                    : `Opens ${fmtDate(s.opens_on)}`
                  : "Opens after the grievance is filed"}
            </p>
            <label className="mt-3 block text-xs">
              <span className="text-muted-foreground">Date filed</span>
              <input
                type="date"
                value={s.filed_on ?? ""}
                disabled={!s.open && !s.filed_on}
                onChange={async (e) => setSteps(await api.setTracker(caseId, s.stage, e.target.value || null))}
                className="bg-background mt-1 block w-full rounded-md border px-2 py-1.5 text-sm disabled:opacity-50"
              />
            </label>
          </li>
        ))}
      </ol>
    </section>
  );
}

function CostPanel({ cost, live }: { cost: Cost; live?: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost of this case</CardTitle>
        <CardDescription>{live ? "Updating as Nemotron works" : "All Nemotron calls for this case"}</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-3 gap-2 text-center">
          <div>
            <dd className="text-2xl font-semibold tabular-nums">{cost.calls}</dd>
            <dt className="text-muted-foreground text-xs">model calls</dt>
          </div>
          <div>
            <dd className="text-2xl font-semibold tabular-nums">
              {((cost.input_tokens + cost.output_tokens) / 1000).toFixed(1)}k
            </dd>
            <dt className="text-muted-foreground text-xs">tokens</dt>
          </div>
          <div>
            <dd className="text-2xl font-semibold tabular-nums">${cost.usd.toFixed(4)}</dd>
            <dt className="text-muted-foreground text-xs">USD</dt>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function ClauseDialog({ caseId, clauseNo, onClose }: { caseId: string; clauseNo: string | null; onClose: () => void }) {
  const [clause, setClause] = useState<Clause | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    setClause(null);
    setErr(false);
    if (clauseNo) api.getClause(caseId, clauseNo).then(setClause).catch(() => setErr(true));
  }, [caseId, clauseNo]);
  return (
    <Dialog open={clauseNo !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Clause {clauseNo}</DialogTitle>
          <DialogDescription className="capitalize">{clause?.tag.replace("_", " ") ?? "Policy wording"}</DialogDescription>
        </DialogHeader>
        {err ? (
          <p className="text-flag text-sm">This clause number isn&apos;t in the uploaded policy.</p>
        ) : clause ? (
          <p className="font-serif leading-relaxed">{clause.text}</p>
        ) : (
          <Loader2 className="text-muted-foreground animate-spin" />
        )}
      </DialogContent>
    </Dialog>
  );
}
