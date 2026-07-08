"use client";

import { memo, useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { useEvents } from "@/hooks/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function AlarmPanelImpl() {
  const { data } = useEvents(20);
  const alarms = useMemo(
    () =>
      (data ?? []).filter(
        (e) => e.risk_level === "critical" || e.risk_level === "high"
      ),
    [data]
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-red-400 flex items-center gap-1.5">
          <AlertTriangle size={13} /> Alarm Log
        </CardTitle>
      </CardHeader>
      <CardContent className="max-h-64 space-y-2 overflow-y-auto">
        {alarms.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500">
            No active alarms
          </div>
        ) : (
          alarms.map((e) => (
            <div
              key={e.event_id}
              className="rounded border border-red-900 bg-red-950/40 p-2 text-[11px]"
            >
              <div className="font-bold text-red-400">
                {e.event_type.toUpperCase()} [{e.risk_level}]
              </div>
              <div className="text-red-200/80">
                {e.description ?? "—"} ({e.equipment_id ?? "Mine"})
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export const AlarmPanel = memo(AlarmPanelImpl);
