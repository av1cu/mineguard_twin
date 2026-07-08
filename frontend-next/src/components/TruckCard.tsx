"use client";

import { memo } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { RiskBadge } from "@/components/ui/badge";
import { useMapStore } from "@/store/mapStore";
import { cn } from "@/lib/utils";
import type { EquipmentStateResponse } from "@/types/api";

function TruckCardImpl({ truck }: { truck: EquipmentStateResponse }) {
  const selectedId = useMapStore((s) => s.selectedEquipmentId);
  const toggle = useMapStore((s) => s.toggleSelectedEquipmentId);
  const selected = selectedId === truck.equipment_id;

  return (
    <button
      onClick={() => toggle(truck.equipment_id)}
      className={cn(
        "w-full rounded-md border p-2.5 text-left transition-colors",
        selected
          ? "border-sky-600 bg-slate-800/80"
          : "border-slate-800 bg-slate-900/60 hover:border-sky-700 hover:bg-slate-800/60"
      )}
    >
      <div className="mb-1 flex items-center justify-between text-xs font-bold">
        <span>
          {truck.equipment_id}{" "}
          <span className="font-normal text-slate-400">
            ({truck.driver_id ?? "—"})
          </span>
        </span>
        <StatusBadge status={truck.status ?? "moving"} />
      </div>
      <div className="flex items-center justify-between text-[11px] text-slate-400">
        <span>Speed: {truck.speed ?? 0} km/h</span>
        <RiskBadge risk={truck.risk_level} />
      </div>
      <div className="mt-1 text-[10px] text-slate-500 font-mono">
        Route: {truck.current_route ?? "—"} · Fatigue: {truck.fatigue_score}%
      </div>
    </button>
  );
}

export const TruckCard = memo(TruckCardImpl);
