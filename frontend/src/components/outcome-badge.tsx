import { OUTCOME_LABEL, type Outcome } from "@/lib/api";
import { cn } from "@/lib/utils";

const STYLE: Record<Outcome, string> = {
  contestable: "bg-contestable-soft text-contestable border-contestable/30",
  unclear: "bg-unclear-soft text-unclear border-unclear/30",
  likely_valid: "bg-valid-soft text-valid border-valid/30",
};

export function OutcomeBadge({ outcome, className }: { outcome: Outcome; className?: string }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold", STYLE[outcome], className)}
    >
      {OUTCOME_LABEL[outcome]}
    </span>
  );
}
