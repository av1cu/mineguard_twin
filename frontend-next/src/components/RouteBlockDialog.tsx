"use client";

import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useBlockRoute } from "@/hooks/queries";
import type { RouteResponse } from "@/types/api";

export function RouteBlockDialog({
  route,
  onClose,
}: {
  route: RouteResponse | null;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const blockRoute = useBlockRoute();

  return (
    <Dialog
      open={Boolean(route)}
      onClose={onClose}
      title={route ? `Block route: ${route.route_id}` : ""}
    >
      {route && (
        <div className="space-y-3 text-sm">
          <p className="text-xs text-slate-400">
            {route.route_name} ({route.from_point} → {route.to_point})
          </p>
          <label className="block text-xs font-semibold text-slate-300">
            Reason for closure
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-slate-700 bg-slate-800 p-2 text-xs text-slate-100 outline-none focus:border-sky-500"
            placeholder="e.g. rockslide detected, road closed for inspection"
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={!reason.trim() || blockRoute.isPending}
              onClick={() => {
                blockRoute.mutate(
                  { routeId: route.route_id, reason: reason.trim() },
                  { onSuccess: onClose }
                );
              }}
            >
              Block route
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  );
}
