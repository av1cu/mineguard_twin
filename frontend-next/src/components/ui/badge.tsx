import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types/api";

export function Badge({
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide border",
        className
      )}
      {...props}
    />
  );
}

const riskClasses: Record<RiskLevel, string> = {
  low: "text-emerald-400 border-emerald-500 bg-emerald-500/10",
  medium: "text-amber-400 border-amber-500 bg-amber-500/10",
  high: "text-red-400 border-red-500 bg-red-500/10",
  critical: "text-red-300 border-red-400 bg-red-500/20",
};

export function RiskBadge({ risk }: { risk: RiskLevel | string }) {
  const cls =
    riskClasses[risk as RiskLevel] ??
    "text-slate-300 border-slate-500 bg-slate-500/10";
  return <Badge className={cls}>{risk}</Badge>;
}
