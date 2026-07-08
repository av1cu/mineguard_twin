"use client";

import { memo } from "react";
import { Slider } from "@/components/ui/slider";
import { useMapStore } from "@/store/mapStore";
import { useSetSimulationSpeed } from "@/hooks/queries";

function SpeedSliderImpl() {
  const speed = useMapStore((s) => s.speedSelection);
  const setSpeed = useMapStore((s) => s.setSpeedSelection);
  const mutate = useSetSimulationSpeed();

  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] text-slate-400">
        <span>Simulation speed</span>
        <span className="font-mono text-slate-200">
          {speed.toFixed(1)} tick/s
        </span>
      </div>
      <Slider
        min={0.5}
        max={20}
        step={0.5}
        value={speed}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          setSpeed(v);
          mutate.mutate(v);
        }}
      />
    </div>
  );
}

export const SpeedSlider = memo(SpeedSliderImpl);
