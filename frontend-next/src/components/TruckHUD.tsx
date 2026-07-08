"use client";

import { memo, useMemo } from "react";
import { useEquipment } from "@/hooks/queries";
import { useMapStore } from "@/store/mapStore";
import { RiskBadge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function TruckHUDImpl() {
  const selectedId = useMapStore((s) => s.selectedEquipmentId);
  const { data } = useEquipment();
  const truck = useMemo(
    () => data?.find((t) => t.equipment_id === selectedId) ?? null,
    [data, selectedId]
  );

  if (!selectedId || !truck) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Truck Telemetry</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-slate-500">
          Select a truck on the map or in the equipment list to view detailed
          telemetry.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{truck.equipment_id}</CardTitle>
        <StatusBadge status={truck.status ?? "moving"} />
      </CardHeader>
      <CardContent className="space-y-1.5 text-[11px]">
        <Row label="Driver" value={truck.driver_id ?? "—"} />
        <Row label="Type" value={truck.equipment_type} />
        <Row label="Route" value={truck.current_route ?? "—"} />
        <Row label="Speed" value={`${truck.speed ?? 0} km/h`} />
        <Row label="Fatigue (PERCLOS)" value={`${truck.fatigue_score}%`} />
        <Row
          label="Position"
          value={`${(truck.current_position_x ?? 0).toFixed(1)}, ${(truck.current_position_y ?? 0).toFixed(1)}`}
        />
        <div className="flex items-center justify-between pt-1">
          <span className="text-slate-400">Risk level</span>
          <RiskBadge risk={truck.risk_level} />
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-semibold text-slate-100">{value}</span>
    </div>
  );
}

export const TruckHUD = memo(TruckHUDImpl);
