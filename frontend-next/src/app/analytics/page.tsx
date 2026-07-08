"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/MetricCard";
import { KpiBarChart } from "@/components/KpiBarChart";
import { KpiLineChart } from "@/components/KpiLineChart";
import { useKpis } from "@/hooks/queries";

export default function AnalyticsPage() {
  const { data: kpis } = useKpis();
  const runs = useMemo(() => kpis ?? [], [kpis]);

  const trendData = useMemo(
    () =>
      runs.map((k, i) => ({
        run: `#${i + 1} ${k.dispatcher_name}`,
        fuel_per_ton: k.fuel_per_ton,
        avg_cycle_time: k.avg_cycle_time,
        safety_events_count: k.safety_events_count,
        idle_time: k.truck_idle_time,
      })),
    [runs]
  );

  const totalTons = runs.reduce((acc, k) => acc + k.produced_tons, 0);
  const totalFuel = runs.reduce((acc, k) => acc + k.total_fuel, 0);
  const totalSafetyEvents = runs.reduce(
    (acc, k) => acc + k.safety_events_count,
    0
  );
  const avgFuelPerTon =
    runs.length > 0 ? totalFuel / Math.max(totalTons, 1) : 0;

  const fuelData = runs.map((k) => ({
    dispatcher_name: k.dispatcher_name,
    value: k.fuel_per_ton,
  }));
  const safetyData = runs.map((k) => ({
    dispatcher_name: k.dispatcher_name,
    value: k.safety_events_count,
  }));

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">Analytics</h1>
        <p className="text-xs text-slate-400">
          Deeper trends across all recorded simulation KPI runs: fuel
          efficiency, safety incidents and cycle-time evolution.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard label="Recorded runs" value={runs.length} />
        <MetricCard label="Total tons produced" value={totalTons.toFixed(1)} accent="emerald" />
        <MetricCard label="Total fuel used (L)" value={totalFuel.toFixed(1)} accent="amber" />
        <MetricCard
          label="Total safety events"
          value={totalSafetyEvents}
          accent={totalSafetyEvents > 0 ? "red" : "emerald"}
        />
      </div>

      {runs.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-xs text-slate-500">
            No KPI runs recorded yet. Head to the Simulation page and run a
            baseline / optimized scenario.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <KpiBarChart
              title="Fuel efficiency (L / ton)"
              dataKeyLabel="L/ton"
              data={fuelData}
            />
            <KpiBarChart
              title="Safety events per run"
              dataKeyLabel="events"
              data={safetyData}
            />
          </div>

          <KpiLineChart
            title="Cycle time & idle time trend across runs"
            data={trendData}
            xKey="run"
            series={[
              { dataKey: "avg_cycle_time", color: "#38bdf8", label: "Avg cycle time (min)" },
              { dataKey: "idle_time", color: "#f59e0b", label: "Idle time (h)" },
            ]}
          />

          <KpiLineChart
            title="Fuel per ton & safety events trend"
            data={trendData}
            xKey="run"
            series={[
              { dataKey: "fuel_per_ton", color: "#22c55e", label: "Fuel per ton (L/t)" },
              { dataKey: "safety_events_count", color: "#ef4444", label: "Safety events" },
            ]}
          />

          <Card>
            <CardHeader>
              <CardTitle>Overall average fuel efficiency</CardTitle>
            </CardHeader>
            <CardContent className="font-mono text-2xl font-bold text-emerald-400">
              {avgFuelPerTon.toFixed(2)}{" "}
              <span className="text-sm font-normal text-slate-400">L/ton (blended across all runs)</span>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
