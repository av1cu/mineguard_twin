"use client";

import { useMemo } from "react";
import { MineCanvas } from "@/components/MineCanvas";
import { MetricCard } from "@/components/MetricCard";
import { AlarmPanel } from "@/components/AlarmPanel";
import { RecommendationsPanel } from "@/components/RecommendationsPanel";
import { PredictiveRiskPanel } from "@/components/PredictiveRiskPanel";
import { SimulationControls } from "@/components/SimulationControls";
import { EquipmentList } from "@/components/EquipmentList";
import { TruckHUD } from "@/components/TruckHUD";
import { useSimulationState } from "@/hooks/queries";

export default function DashboardPage() {
  const { data } = useSimulationState();

  const runningTrucks = useMemo(
    () => (data?.trucks ?? []).filter((t) => t.status !== "stopped").length,
    [data]
  );
  const totalTrucks = data?.trucks.length ?? 0;
  const activeRisks = useMemo(
    () =>
      (data?.trucks ?? []).filter(
        (t) => t.risk_level === "high" || t.risk_level === "critical"
      ).length,
    [data]
  );

  return (
    <div className="flex h-full flex-col gap-3 p-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="Current tick" value={`${data?.current_tick ?? 0}/${data?.max_ticks ?? 0}`} />
        <MetricCard label="Fleet operational" value={`${runningTrucks}/${totalTrucks}`} accent="emerald" />
        <MetricCard label="High-risk trucks" value={activeRisks} accent={activeRisks > 0 ? "red" : "emerald"} />
        <MetricCard label="Dispatcher" value={data?.dispatcher ?? "—"} accent="sky" />
      </div>

      <div className="grid flex-1 grid-cols-1 gap-3 overflow-hidden lg:grid-cols-[1fr_380px]">
        <div className="min-h-[420px] overflow-hidden rounded-lg border border-slate-800">
          <MineCanvas />
        </div>
        <div className="flex flex-col gap-3 overflow-y-auto pr-1">
          <SimulationControls />
          <TruckHUD />
          <div className="rounded-lg border border-slate-800 bg-[#0b0f19]/80 p-3">
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-sky-400">
              Fleet telemetry
            </div>
            <EquipmentList />
          </div>
          <AlarmPanel />
          <RecommendationsPanel />
          <PredictiveRiskPanel />
        </div>
      </div>
    </div>
  );
}
