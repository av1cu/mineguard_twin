"use client";

import { memo } from "react";
import { Radar } from "lucide-react";
import { usePredictiveRisks } from "@/hooks/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function PredictiveRiskPanelImpl() {
  const { data } = usePredictiveRisks();
  const risks = data ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-amber-400 flex items-center gap-1.5">
          <Radar size={13} /> Predictive Safety
        </CardTitle>
      </CardHeader>
      <CardContent className="max-h-64 space-y-2 overflow-y-auto">
        {risks.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500">
            Distance control nominal
          </div>
        ) : (
          risks.map((r, i) => (
            <div
              key={`${r.equipment1}-${r.equipment2}-${i}`}
              className="animate-pulse rounded border border-amber-900 bg-amber-950/40 p-2 text-[11px]"
            >
              <div className="mb-0.5 flex justify-between font-bold text-amber-400">
                <span>Collision risk</span>
                <span>{r.risk_score.toFixed(0)}%</span>
              </div>
              <div className="mb-1 text-amber-200">
                {r.equipment1} ↔ {r.equipment2}
              </div>
              <div className="mb-1 text-amber-300">{r.recommendation}</div>
              <div className="font-mono text-[10px] text-amber-500/80">
                Predicted: {r.predicted_time}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export const PredictiveRiskPanel = memo(PredictiveRiskPanelImpl);
