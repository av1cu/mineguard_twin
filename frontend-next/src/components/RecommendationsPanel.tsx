"use client";

import { memo } from "react";
import { Lightbulb } from "lucide-react";
import { useAcceptRecommendation, useRecommendations } from "@/hooks/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function RecommendationsPanelImpl() {
  const { data } = useRecommendations();
  const accept = useAcceptRecommendation();
  const recs = data ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Lightbulb size={13} /> Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent className="max-h-72 space-y-2 overflow-y-auto">
        {recs.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500">
            No active recommendations
          </div>
        ) : (
          recs.map((r) => (
            <div
              key={r.id}
              className="rounded border border-slate-700 bg-slate-800/60 p-2 text-[11px]"
            >
              <div className="mb-1 flex justify-between font-bold text-sky-400">
                <span>{r.title ?? r.event_type ?? "Recommendation"}</span>
                <span className="font-normal text-slate-400">
                  {r.category ?? r.risk_level ?? ""}
                </span>
              </div>
              <div className="mb-1 text-slate-300">{r.description}</div>
              {r.recommendation && (
                <div className="mb-1 text-amber-300">→ {r.recommendation}</div>
              )}
              {r.effects && (
                <div className="mb-1 space-y-0.5 rounded border border-slate-800 bg-slate-950 px-1.5 py-1 font-mono text-[10px] text-emerald-400">
                  {r.effects.expected_cycle_time_change != null && (
                    <div>Cycle: {String(r.effects.expected_cycle_time_change)}</div>
                  )}
                  {r.effects.expected_fuel_change != null && (
                    <div>Fuel: {String(r.effects.expected_fuel_change)}</div>
                  )}
                  {r.effects.expected_productivity_change != null && (
                    <div>
                      Output: {String(r.effects.expected_productivity_change)}
                    </div>
                  )}
                </div>
              )}
              <Button
                size="sm"
                variant="primary"
                onClick={() => accept.mutate(r.id)}
                disabled={accept.isPending}
              >
                Accept &amp; apply
              </Button>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export const RecommendationsPanel = memo(RecommendationsPanelImpl);
