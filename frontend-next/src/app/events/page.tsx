"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { RiskBadge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { EventDetailDialog } from "@/components/EventDetailDialog";
import { useEvents } from "@/hooks/queries";
import type { EventResponse } from "@/types/api";

const ALL = "All";

export default function EventsPage() {
  const { data } = useEvents(200);
  const events = useMemo(() => data ?? [], [data]);
  const [moduleFilter, setModuleFilter] = useState(ALL);
  const [riskFilter, setRiskFilter] = useState(ALL);
  const [selectedEvent, setSelectedEvent] = useState<EventResponse | null>(
    null
  );

  const modules = useMemo(
    () => [ALL, ...Array.from(new Set(events.map((e) => e.source_module)))],
    [events]
  );
  const risks = useMemo(
    () => [ALL, ...Array.from(new Set(events.map((e) => e.risk_level)))],
    [events]
  );

  const filtered = useMemo(
    () =>
      events.filter(
        (e) =>
          (moduleFilter === ALL || e.source_module === moduleFilter) &&
          (riskFilter === ALL || e.risk_level === riskFilter)
      ),
    [events, moduleFilter, riskFilter]
  );

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">
          Unified Safety Event Center
        </h1>
        <p className="text-xs text-slate-400">
          Centralized log of events from mine logistics simulation (MineOps),
          slope/road CV monitoring, and driver-state CV monitoring.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <div>
          <label className="mb-1 block text-[11px] text-slate-400">
            Source module
          </label>
          <Select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)}>
            {modules.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-[11px] text-slate-400">
            Risk level
          </label>
          <Select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
            {risks.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Event log (showing {filtered.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No events recorded yet.
            </div>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>ID</TH>
                  <TH>Time</TH>
                  <TH>Module</TH>
                  <TH>Type</TH>
                  <TH>Risk</TH>
                  <TH>Score</TH>
                  <TH>Equipment</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {filtered.map((e) => (
                  <TR
                    key={e.event_id}
                    className="cursor-pointer"
                    onClick={() => setSelectedEvent(e)}
                  >
                    <TD>{e.event_id}</TD>
                    <TD>{e.event_time}</TD>
                    <TD>{e.source_module}</TD>
                    <TD>{e.event_type}</TD>
                    <TD>
                      <RiskBadge risk={e.risk_level} />
                    </TD>
                    <TD>{e.risk_score}</TD>
                    <TD>{e.equipment_id ?? "—"}</TD>
                    <TD>
                      <StatusBadge status={e.status} />
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <EventDetailDialog
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
}
