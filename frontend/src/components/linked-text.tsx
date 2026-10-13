"use client";

import type { Issue } from "@/lib/api";
import { Fragment, type ReactNode } from "react";

const CLAUSE_GROUP = String.raw`\b(clauses?\s+)(\d+(?:\.\d+)*(?:\s*(?:,|and|&|/)\s*\d+(?:\.\d+)*)*)`;
const URL = String.raw`https?:\/\/[^\s)\]>"']+`;
const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * Renders draft or verdict text: clause numbers become buttons that open the clause, valid URLs become links,
 * and anything the verifier flagged (unknown clause, unmatched date, unstored URL) is marked red.
 */
export function LinkedText({
  text,
  issues = [],
  onClause,
}: {
  text: string;
  issues?: Issue[];
  onClause: (no: string) => void;
}) {
  const badClauses = new Set(issues.filter((i) => i.kind === "clause").map((i) => i.value));
  const badOther = issues.filter((i) => i.kind === "date" || i.kind === "url").map((i) => i.value);
  const parts = [CLAUSE_GROUP, ...(badOther.length ? [badOther.map(escape).join("|")] : []), URL];
  const re = new RegExp(parts.map((p) => `(?:${p})`).join("|"), "gi");

  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    const i = m.index ?? 0;
    out.push(text.slice(last, i));
    last = i + m[0].length;
    if (m[1] !== undefined) {
      // clause reference: keep separators, link each number
      out.push(m[1]);
      for (const [j, piece] of m[2].split(/(\d+(?:\.\d+)*)/).entries()) {
        if (j % 2 === 0) out.push(piece);
        else if (badClauses.has(piece))
          out.push(
            <mark key={`${i}-${j}`} className="flag" title="Not in this policy's clause index">
              {piece}
            </mark>,
          );
        else
          out.push(
            <button key={`${i}-${j}`} type="button" className="clause-link" onClick={() => onClause(piece)}>
              {piece}
            </button>,
          );
      }
    } else if (badOther.some((v) => v.toLowerCase() === m[0].toLowerCase())) {
      out.push(
        <mark key={i} className="flag" title="Not found in computed dates or stored sources">
          {m[0]}
        </mark>,
      );
    } else {
      out.push(
        <a key={i} href={m[0]} target="_blank" rel="noreferrer" className="underline underline-offset-2 break-all">
          {m[0]}
        </a>,
      );
    }
  }
  out.push(text.slice(last));
  return <>{out.map((n, k) => <Fragment key={k}>{n}</Fragment>)}</>;
}
