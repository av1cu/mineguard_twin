"use client";

import { memo, useMemo } from "react";
import { useSimulationState } from "@/hooks/queries";
import { TruckCard } from "@/components/TruckCard";

function EquipmentListImpl() {
  const { data } = useSimulationState();
  const trucks = useMemo(() => data?.trucks ?? [], [data]);

  if (trucks.length === 0) {
    return (
      <div className="py-6 text-center text-xs text-slate-500">
        No active equipment. Start the simulation.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {trucks.map((t) => (
        <TruckCard key={t.equipment_id} truck={t} />
      ))}
    </div>
  );
}

export const EquipmentList = memo(EquipmentListImpl);
