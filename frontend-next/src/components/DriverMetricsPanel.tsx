import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/MetricCard";
import type { DriverEyeState } from "@/types/api";

function eyeStateClasses(state: DriverEyeState | undefined): string {
  if (state === "OPEN") return "text-emerald-400 border-emerald-500 bg-emerald-500/10";
  if (state === "CLOSED") return "text-red-400 border-red-500 bg-red-500/10";
  if (state === "PARTIALLY CLOSED")
    return "text-amber-400 border-amber-500 bg-amber-500/10";
  return "text-slate-400 border-slate-600 bg-slate-500/10";
}

interface DriverMetricsPanelProps {
  eyeState?: DriverEyeState;
  isYawning?: boolean;
  isDistracted?: boolean;
  gazeLabel?: string;
  smoothedEar?: number;
  mar?: number;
  perclos?: number;
}

export function DriverMetricsPanel({
  eyeState,
  isYawning,
  isDistracted,
  gazeLabel,
  smoothedEar,
  mar,
  perclos,
}: DriverMetricsPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={eyeStateClasses(eyeState)}>
          {eyeState ?? "N/A"}
        </Badge>
        <Badge
          className={
            isYawning
              ? "text-red-400 border-red-500 bg-red-500/10"
              : "text-emerald-400 border-emerald-500 bg-emerald-500/10"
          }
        >
          {isYawning ? "ЗЕВОТА" : "НОРМА"}
        </Badge>
        <Badge
          className={
            isDistracted
              ? "text-red-400 border-red-500 bg-red-500/10"
              : "text-emerald-400 border-emerald-500 bg-emerald-500/10"
          }
        >
          {isDistracted ? gazeLabel ?? "LOOKING AWAY" : "НА ДОРОГУ"}
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard
          label="Smoothed EAR"
          value={smoothedEar !== undefined ? smoothedEar.toFixed(3) : "—"}
          accent="sky"
        />
        <MetricCard
          label="MAR"
          value={mar !== undefined ? mar.toFixed(3) : "—"}
          accent="sky"
        />
        <MetricCard
          label="PERCLOS"
          value={perclos !== undefined ? perclos.toFixed(1) : "—"}
          unit="%"
          accent="amber"
        />
      </div>
    </div>
  );
}
