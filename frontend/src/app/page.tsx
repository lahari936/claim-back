"use client";

import { OutcomeBadge } from "@/components/outcome-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, fmtDate, type CaseSummary } from "@/lib/api";
import { cn } from "@/lib/utils";
import { FileText, Loader2, Trash2, Upload, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp";
const SAMPLES = [
  { id: "case_a", label: "A", title: "Pre-existing disease, but the history began after the policy started" },
  { id: "case_b", label: "B", title: "Waiting period that had already ended" },
  { id: "case_c", label: "C", title: "Genuine waiting-period exclusion" },
  { id: "case_d", label: "D", title: "Not medically necessary, with a photographed discharge summary" },
];

export default function Home() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseSummary[] | null>(null);

  useEffect(() => {
    api.listCases().then(setCases).catch(() => setCases([]));
  }, []);

  const add = (list: FileList | null) => {
    if (!list) return;
    setFiles((prev) => [...prev, ...Array.from(list).filter((f) => !prev.some((p) => p.name === f.name))]);
  };

  const loadSample = async (id: string) => {
    const summary = id === "case_d" ? "discharge_summary_photo.png" : "discharge_summary.pdf";
    const paths = ["policy_wording.pdf", `${id}/rejection_letter.pdf`, `${id}/${summary}`];
    const loaded = await Promise.all(
      paths.map(async (p) => new File([await (await fetch(`/samples/${p}`)).blob()], p.split("/").pop()!)),
    );
    setFiles(loaded);
  };

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const { id } = await api.createCase(files);
      router.push(`/cases/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this case and all its files? This cannot be undone.")) return;
    await api.deleteCase(id);
    setCases((c) => c?.filter((x) => x.id !== id) ?? null);
  };

  return (
    <div className="space-y-12">
      <section className="grid gap-8 lg:grid-cols-[1fr_1.1fr] lg:items-start">
        <div className="space-y-4 lg:pt-6">
          <h1 className="font-serif text-4xl leading-tight font-semibold tracking-tight sm:text-5xl">
            Was your health claim rejected fairly?
          </h1>
          <p className="text-muted-foreground max-w-prose text-lg">
            Upload the rejection letter, your policy wording and the hospital discharge summary. ClaimBack reads the
            clause the insurer cited, does the date maths, checks IRDAI guidance and tells you which side is stronger.
            If it is worth contesting, you get a grievance letter, a Bima Bharosa complaint and an Ombudsman draft.
          </p>
          <ul className="text-muted-foreground space-y-1 text-sm">
            <li>Covers pre-existing disease, waiting period, non-disclosure and “not medically necessary”.</li>
            <li>Every clause, date and link in a draft is checked; anything unverified is marked red.</li>
          </ul>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">New case</CardTitle>
            <CardDescription>PDFs or photos. Each file is labelled automatically.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <button
              type="button"
              onClick={() => input.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                add(e.dataTransfer.files);
              }}
              className={cn(
                "flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
                dragging ? "border-primary bg-accent" : "hover:bg-muted",
              )}
            >
              <Upload className="text-primary size-7" />
              <span className="font-medium">Drop files here or click to choose</span>
              <span className="text-muted-foreground text-sm">Rejection letter · Policy wording · Discharge summary</span>
            </button>
            <input
              ref={input}
              type="file"
              multiple
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => {
                add(e.target.files);
                e.target.value = "";
              }}
            />
            {files.length > 0 && (
              <ul className="divide-y rounded-lg border">
                {files.map((f) => (
                  <li key={f.name} className="flex items-center gap-3 px-3 py-2 text-sm">
                    <FileText className="text-muted-foreground size-4 shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{f.name}</span>
                    <span className="text-muted-foreground shrink-0 text-xs">{(f.size / 1024).toFixed(0)} KB</span>
                    <button
                      type="button"
                      aria-label={`Remove ${f.name}`}
                      onClick={() => setFiles((p) => p.filter((x) => x !== f))}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">Try a synthetic sample:</span>
              {SAMPLES.map((s) => (
                <Button key={s.id} variant="outline" size="sm" title={s.title} onClick={() => loadSample(s.id)}>
                  {s.label}
                </Button>
              ))}
            </div>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <Button className="w-full" size="lg" disabled={!files.length || busy} onClick={submit}>
              {busy && <Loader2 className="animate-spin" />}
              Check my claim
            </Button>
            <p className="text-muted-foreground text-xs">
              Your files stay with this case until you delete it. Use synthetic or redacted documents for demos.
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl font-semibold">Your cases</h2>
        {cases === null ? (
          <p className="text-muted-foreground text-sm">Loading…</p>
        ) : cases.length === 0 ? (
          <p className="text-muted-foreground text-sm">No cases yet.</p>
        ) : (
          <ul className="bg-card divide-y rounded-xl border">
            {cases.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3">
                <Link href={`/cases/${c.id}`} className="min-w-0 flex-1 hover:underline">
                  <span className="font-medium">{c.claim_no ?? "Claim being read…"}</span>
                  {c.insurer && <span className="text-muted-foreground"> · {c.insurer}</span>}
                </Link>
                <span className="text-muted-foreground text-xs">{fmtDate(c.created_at.slice(0, 10))}</span>
                {c.outcome ? (
                  <OutcomeBadge outcome={c.outcome} />
                ) : (
                  <span className="text-muted-foreground text-xs capitalize">{c.status}</span>
                )}
                <Button variant="ghost" size="icon" aria-label="Delete case" onClick={() => remove(c.id)}>
                  <Trash2 />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
