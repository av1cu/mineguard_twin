"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { RiskBadge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { RouteBlockDialog } from "@/components/RouteBlockDialog";
import { useRoutes, useUnblockRoute } from "@/hooks/queries";
import type { RouteResponse } from "@/types/api";

export default function RoutesPage() {
  const { data } = useRoutes();
  const routes = data ?? [];
  const unblock = useUnblockRoute();
  const [blockTarget, setBlockTarget] = useState<RouteResponse | null>(null);

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">Road Network</h1>
        <p className="text-xs text-slate-400">
          Manage the mine road network: block routes for hazard mitigation or
          reopen them once cleared.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Routes ({routes.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {routes.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No route data available yet.
            </div>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>ID</TH>
                  <TH>Name</TH>
                  <TH>From</TH>
                  <TH>To</TH>
                  <TH>Distance (km)</TH>
                  <TH>Status</TH>
                  <TH>Risk</TH>
                  <TH>Blocked reason</TH>
                  <TH>Action</TH>
                </TR>
              </THead>
              <TBody>
                {routes.map((r) => (
                  <TR key={r.route_id}>
                    <TD>{r.route_id}</TD>
                    <TD>{r.route_name}</TD>
                    <TD>{r.from_point ?? "—"}</TD>
                    <TD>{r.to_point ?? "—"}</TD>
                    <TD>{r.distance_km.toFixed(2)}</TD>
                    <TD>
                      <StatusBadge status={r.status} />
                    </TD>
                    <TD>
                      <RiskBadge risk={r.risk_level} />
                    </TD>
                    <TD>{r.blocked_reason ?? "—"}</TD>
                    <TD>
                      {r.status === "blocked" ? (
                        <Button
                          size="sm"
                          variant="primary"
                          disabled={unblock.isPending}
                          onClick={() => unblock.mutate(r.route_id)}
                        >
                          Unblock
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => setBlockTarget(r)}
                        >
                          Block
                        </Button>
                      )}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <RouteBlockDialog route={blockTarget} onClose={() => setBlockTarget(null)} />
    </div>
  );
}
