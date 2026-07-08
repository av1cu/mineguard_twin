"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TruckSelector } from "@/components/TruckSelector";
import { DriverFatiguePanel } from "@/components/DriverFatiguePanel";
import { useMapStore } from "@/store/mapStore";

export default function DriverCvPage() {
  const truck = useMapStore((s) => s.truckSelection);

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">Driver Fatigue CV</h1>
        <p className="text-xs text-slate-400">
          Real-time computer-vision driver fatigue and distraction monitoring
          using MediaPipe face-mesh landmarks. Eye-aspect-ratio (EAR) tracks
          eyelid closure, mouth-aspect-ratio (MAR) detects yawning, and PERCLOS
          (percentage of eye closure over time) estimates drowsiness. Frames
          are streamed from your webcam to the backend at ~10 FPS for
          analysis; the annotated frame with detected landmarks is returned
          and displayed below.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Truck / Equipment</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-w-xs">
            <TruckSelector />
          </div>
        </CardContent>
      </Card>

      <DriverFatiguePanel truckId={truck} />
    </div>
  );
}
