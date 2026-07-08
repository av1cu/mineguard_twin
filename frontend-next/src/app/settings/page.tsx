"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMapStore } from "@/store/mapStore";
import { BACKEND_URL } from "@/lib/api";

export default function SettingsPage() {
  const displaySettings = useMapStore((s) => s.displaySettings);
  const toggleDisplaySetting = useMapStore((s) => s.toggleDisplaySetting);

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">Settings</h1>
        <p className="text-xs text-slate-400">
          Runtime configuration for the SCADA console. Backend URL is
          controlled via the NEXT_PUBLIC_BACKEND_URL build-time environment
          variable.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Backend connection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <Row label="Backend base URL" value={BACKEND_URL} />
          <Row label="Simulation state poll interval" value="500 ms" />
          <Row label="Events / recommendations poll interval" value="1000 ms" />
          <Row label="KPI poll interval" value="2000 ms" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Map display</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <ToggleRow
            label="Show grid"
            checked={displaySettings.showGrid}
            onChange={() => toggleDisplaySetting("showGrid")}
          />
          <ToggleRow
            label="Show predictive risk lines"
            checked={displaySettings.showPredictiveLines}
            onChange={() => toggleDisplaySetting("showPredictiveLines")}
          />
          <ToggleRow
            label="Show equipment labels"
            checked={displaySettings.showLabels}
            onChange={() => toggleDisplaySetting("showLabels")}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Defaults</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <Row label="Default dispatcher" value="NaiveDispatcher" />
          <Row label="Theme" value="Dark industrial SCADA (fixed)" />
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-slate-800/60 py-1.5">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono text-slate-100">{value}</span>
    </div>
  );
}

function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex items-center justify-between border-b border-slate-800/60 py-1.5">
      <span className="text-slate-400">{label}</span>
      <button
        onClick={onChange}
        className={`h-5 w-9 rounded-full transition-colors ${
          checked ? "bg-sky-600" : "bg-slate-700"
        }`}
      >
        <span
          className={`block h-4 w-4 rounded-full bg-white transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}
