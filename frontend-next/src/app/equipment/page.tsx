"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { RiskBadge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { useEquipment } from "@/hooks/queries";

export default function EquipmentPage() {
  const { data } = useEquipment();
  const equipment = data ?? [];

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">Equipment Roster</h1>
        <p className="text-xs text-slate-400">
          Full fleet roster with live status, risk level, fatigue score, and
          assigned driver.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Fleet ({equipment.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {equipment.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No equipment telemetry available. Start the simulation to
              populate the fleet.
            </div>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>ID</TH>
                  <TH>Type</TH>
                  <TH>Driver</TH>
                  <TH>Route</TH>
                  <TH>Position (x, y)</TH>
                  <TH>Speed</TH>
                  <TH>Status</TH>
                  <TH>Risk</TH>
                  <TH>Fatigue</TH>
                </TR>
              </THead>
              <TBody>
                {equipment.map((eq) => (
                  <TR key={eq.equipment_id}>
                    <TD>{eq.equipment_id}</TD>
                    <TD>{eq.equipment_type}</TD>
                    <TD>{eq.driver_id ?? "—"}</TD>
                    <TD>{eq.current_route ?? "—"}</TD>
                    <TD>
                      {(eq.current_position_x ?? 0).toFixed(1)},{" "}
                      {(eq.current_position_y ?? 0).toFixed(1)}
                    </TD>
                    <TD>{eq.speed ?? 0} km/h</TD>
                    <TD>
                      <StatusBadge status={eq.status ?? "moving"} />
                    </TD>
                    <TD>
                      <RiskBadge risk={eq.risk_level} />
                    </TD>
                    <TD>{eq.fatigue_score}%</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
