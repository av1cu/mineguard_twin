import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string | number;
  unit?: string;
  accent?: "sky" | "amber" | "red" | "emerald";
}) {
  const accentClass =
    accent === "amber"
      ? "text-amber-400"
      : accent === "red"
      ? "text-red-400"
      : accent === "emerald"
      ? "text-emerald-400"
      : "text-sky-400";

  return (
    <Card>
      <CardContent className="text-center py-4">
        <div
          className={cn(
            "font-mono text-2xl font-bold tabular-nums",
            accentClass
          )}
        >
          {value}
          {unit ? (
            <span className="ml-1 text-sm font-normal text-slate-400">
              {unit}
            </span>
          ) : null}
        </div>
        <div className="mt-1 text-[11px] uppercase tracking-wide text-slate-400">
          {label}
        </div>
      </CardContent>
    </Card>
  );
}
