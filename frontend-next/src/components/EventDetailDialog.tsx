"use client";

import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/ui/badge";
import { useUpdateEventStatus } from "@/hooks/queries";
import type { EventResponse } from "@/types/api";

export function EventDetailDialog({
  event,
  onClose,
}: {
  event: EventResponse | null;
  onClose: () => void;
}) {
  const updateStatus = useUpdateEventStatus();

  return (
    <Dialog
      open={Boolean(event)}
      onClose={onClose}
      title={event ? `Event: ${event.event_type.toUpperCase()}` : ""}
    >
      {event && (
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-2 text-[12px] font-mono text-slate-300">
            <div>ID: {event.event_id}</div>
            <div>Time: {event.event_time}</div>
            <div>Module: {event.source_module}</div>
            <div>Score: {event.risk_score} / 100</div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Risk level:</span>
            <RiskBadge risk={event.risk_level} />
          </div>
          {event.equipment_id && (
            <div className="text-xs text-slate-300">
              Equipment: <span className="font-mono">{event.equipment_id}</span>{" "}
              (Driver: <span className="font-mono">{event.driver_id ?? "—"}</span>)
            </div>
          )}
          {event.route_id && (
            <div className="text-xs text-slate-300">
              Route/section: <span className="font-mono">{event.route_id}</span>{" "}
              (<span className="font-mono">{event.section_id ?? "—"}</span>)
            </div>
          )}
          <div>
            <div className="mb-1 text-xs font-bold uppercase text-slate-400">
              Description
            </div>
            <div className="rounded border border-slate-700 bg-slate-800/60 p-2 text-xs text-slate-200">
              {event.description ?? "No description available."}
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-bold uppercase text-slate-400">
              Recommendation
            </div>
            <div className="rounded border border-amber-800 bg-amber-950/40 p-2 text-xs text-amber-200">
              {event.recommendation ?? "No recommendation available."}
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-bold uppercase text-slate-400">
              Evidence (camera frame)
            </div>
            <div className="flex h-32 items-center justify-center rounded border border-dashed border-slate-700 bg-slate-950 text-[11px] text-slate-500">
              {event.evidence_path
                ? "Evidence frame is stored server-side only; not available over the API."
                : "No evidence frame available for this event type."}
            </div>
          </div>
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-slate-400">
              Status: <span className="font-mono uppercase">{event.status}</span>
            </span>
            {event.status === "new" ? (
              <Button
                variant="primary"
                size="sm"
                disabled={updateStatus.isPending}
                onClick={() =>
                  updateStatus.mutate({
                    eventId: event.event_id,
                    status: "resolved",
                  })
                }
              >
                Acknowledge / Resolve
              </Button>
            ) : (
              <span className="text-xs text-emerald-400">Handled by dispatcher</span>
            )}
          </div>
        </div>
      )}
    </Dialog>
  );
}
