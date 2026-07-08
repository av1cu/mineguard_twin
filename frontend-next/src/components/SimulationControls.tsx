"use client";

import { memo } from "react";
import { Play, Pause, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DispatcherSelector } from "@/components/DispatcherSelector";
import { SpeedSlider } from "@/components/SpeedSlider";
import { useMapStore } from "@/store/mapStore";
import {
  useResetSimulation,
  useSimulationState,
  useStartSimulation,
  useStopSimulation,
} from "@/hooks/queries";

function SimulationControlsImpl() {
  const dispatcher = useMapStore((s) => s.dispatcherSelection);
  const speed = useMapStore((s) => s.speedSelection);
  const resetView = useMapStore((s) => s.resetView);
  const setSelectedEquipmentId = useMapStore((s) => s.setSelectedEquipmentId);

  const { data: simState } = useSimulationState();
  const start = useStartSimulation();
  const stop = useStopSimulation();
  const reset = useResetSimulation();

  const isRunning = simState?.is_running ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Commands</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Button
            variant="primary"
            className="flex-1"
            disabled={isRunning || start.isPending}
            onClick={() => start.mutate({ dispatcher, speed })}
          >
            <Play size={14} /> Start
          </Button>
          <Button
            className="flex-1"
            disabled={!isRunning || stop.isPending}
            onClick={() => stop.mutate()}
          >
            <Pause size={14} /> Pause
          </Button>
          <Button
            variant="danger"
            className="flex-1"
            disabled={reset.isPending}
            onClick={() => {
              reset.mutate();
              setSelectedEquipmentId(null);
              resetView();
            }}
          >
            <RotateCcw size={14} /> Reset
          </Button>
        </div>
        <div>
          <div className="mb-1 text-[11px] text-slate-400">Dispatcher</div>
          <DispatcherSelector />
        </div>
        <SpeedSlider />
      </CardContent>
    </Card>
  );
}

export const SimulationControls = memo(SimulationControlsImpl);
