"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { KpiBarChart } from "@/components/KpiBarChart";
import { DISPATCHER_OPTIONS } from "@/components/DispatcherSelector";
import {
  useKpis,
  useRunScenario,
  useSimulationState,
  useStartSimulation,
} from "@/hooks/queries";
import type { ScenarioRunRequest } from "@/types/api";

type ScenarioType =
  | "disable_truck"
  | "block_route"
  | "reduce_speed"
  | "increase_load";

const TRUCK_IDS = ["TRUCK-01", "TRUCK-02", "TRUCK-03", "TRUCK-04", "TRUCK-05"];
const ROUTE_IDS = ["ROUTE-01", "ROUTE-02", "ROUTE-03", "ROUTE-04"];
const SHOVEL_IDS = ["Shovel-01", "Shovel-02", "Shovel-03"];

export default function SimulationPage() {
  const { data: simState } = useSimulationState();
  const { data: kpis } = useKpis();
  const start = useStartSimulation();
  const runScenario = useRunScenario();

  const [scenarioType, setScenarioType] =
    useState<ScenarioType>("disable_truck");
  const [scenarioDispatcher, setScenarioDispatcher] = useState("NaiveDispatcher");
  const [disabledTruck, setDisabledTruck] = useState(TRUCK_IDS[0]);
  const [blockedRoute, setBlockedRoute] = useState(ROUTE_IDS[0]);
  const [reducedSpeedTruck, setReducedSpeedTruck] = useState(TRUCK_IDS[0]);
  const [reducedSpeedValue, setReducedSpeedValue] = useState(5);
  const [increasedLoadShovel, setIncreasedLoadShovel] = useState(SHOVEL_IDS[0]);
  const [increasedLoadValue, setIncreasedLoadValue] = useState(5);

  const progressPct = useMemo(() => {
    if (!simState || !simState.max_ticks) return 0;
    return Math.min(100, (simState.current_tick / simState.max_ticks) * 100);
  }, [simState]);

  const baselineKpi = kpis?.find((k) => k.dispatcher_name === "NaiveDispatcher");
  const optimizedKpi = kpis?.find((k) => k.dispatcher_name === "SmartDispatcher");

  const fuelData = useMemo(
    () =>
      (kpis ?? []).map((k) => ({
        dispatcher_name: k.dispatcher_name,
        value: k.fuel_per_ton,
      })),
    [kpis]
  );
  const safetyData = useMemo(
    () =>
      (kpis ?? []).map((k) => ({
        dispatcher_name: k.dispatcher_name,
        value: k.safety_events_count,
      })),
    [kpis]
  );

  function runWhatIf() {
    const payload: ScenarioRunRequest = { dispatcher: scenarioDispatcher };
    if (scenarioType === "disable_truck") payload.disabled_truck = disabledTruck;
    if (scenarioType === "block_route") payload.blocked_route = blockedRoute;
    if (scenarioType === "reduce_speed") {
      payload.reduced_speed_truck = reducedSpeedTruck;
      payload.reduced_speed_value = reducedSpeedValue;
    }
    if (scenarioType === "increase_load") {
      payload.increased_load_shovel = increasedLoadShovel;
      payload.increased_load_value = increasedLoadValue;
    }
    runScenario.mutate(payload);
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-lg font-bold text-sky-400">
          OpenMines Simulation Control
        </h1>
        <p className="text-xs text-slate-400">
          Configure and run the mine logistics simulation on the OpenMines /
          SimPy backend. Compare a baseline (fixed-route) dispatcher against an
          AI-driven safety and fuel-aware dispatcher.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>1. Baseline scenario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-slate-300">
            <ul className="list-disc space-y-1 pl-4">
              <li>Dispatcher: Naive / fixed dispatcher</li>
              <li>Ignores rockslides, cracks and blocked roads</li>
              <li>No automatic stop on fatigue detection</li>
              <li>Higher idle time and queueing losses</li>
            </ul>
            <Button
              variant="primary"
              className="w-full"
              disabled={start.isPending}
              onClick={() =>
                start.mutate({ dispatcher: "NaiveDispatcher", speed: 30.0 })
              }
            >
              Run baseline simulation
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>2. Optimized scenario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-slate-300">
            <ul className="list-disc space-y-1 pl-4">
              <li>Dispatcher: EnergyAwareSafetyDispatcher</li>
              <li>Dynamically routes around hazardous sections</li>
              <li>Auto-stops equipment on microsleep detection</li>
              <li>Minimizes idle time and fuel consumption</li>
            </ul>
            <Button
              variant="primary"
              className="w-full"
              disabled={start.isPending}
              onClick={() =>
                start.mutate({ dispatcher: "SmartDispatcher", speed: 30.0 })
              }
            >
              Run optimized simulation
            </Button>
          </CardContent>
        </Card>
      </div>

      {simState && (
        <Card>
          <CardContent className="py-3">
            <div className="mb-1 flex justify-between text-xs text-slate-400">
              <span>
                Tick {simState.current_tick} / {simState.max_ticks} (
                {simState.dispatcher})
              </span>
              <span>{simState.is_running ? "Running…" : "Idle"}</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full bg-sky-500 transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Result comparison (Baseline vs Optimized)</CardTitle>
        </CardHeader>
        <CardContent>
          {kpis && kpis.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH>Dispatcher</TH>
                  <TH>Trips</TH>
                  <TH>Tons produced</TH>
                  <TH>Avg cycle (min)</TH>
                  <TH>Idle time (h)</TH>
                  <TH>Fuel (L)</TH>
                  <TH>L/ton</TH>
                  <TH>Safety events</TH>
                </TR>
              </THead>
              <TBody>
                {kpis.map((k) => (
                  <TR key={k.run_id}>
                    <TD>{k.dispatcher_name}</TD>
                    <TD>{k.completed_trips}</TD>
                    <TD>{k.produced_tons.toFixed(1)}</TD>
                    <TD>{k.avg_cycle_time.toFixed(1)}</TD>
                    <TD>{k.truck_idle_time.toFixed(2)}</TD>
                    <TD>{k.total_fuel.toFixed(1)}</TD>
                    <TD>{k.fuel_per_ton.toFixed(2)}</TD>
                    <TD>{k.safety_events_count}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : (
            <div className="py-6 text-center text-xs text-slate-500">
              No saved simulation results yet. Run both scenarios above.
            </div>
          )}
        </CardContent>
      </Card>

      {kpis && kpis.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <KpiBarChart
            title="Efficiency: fuel per ton (L/t)"
            dataKeyLabel="L/ton"
            data={fuelData}
          />
          <KpiBarChart
            title="Safety: hazardous events count"
            dataKeyLabel="events"
            data={safetyData}
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>What-if scenario modelling</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-slate-400">
            Run an alternative copy of the simulation with modified parameters
            (disable equipment, block a route, reduce truck speed or increase
            shovel load time) without affecting the primary run.
          </p>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-[11px] text-slate-400">
                Scenario type
              </label>
              <Select
                className="w-full"
                value={scenarioType}
                onChange={(e) =>
                  setScenarioType(e.target.value as ScenarioType)
                }
              >
                <option value="disable_truck">Disable a truck</option>
                <option value="block_route">Block a route</option>
                <option value="reduce_speed">Reduce truck speed</option>
                <option value="increase_load">Increase shovel load time</option>
              </Select>
              <label className="mb-1 mt-2 block text-[11px] text-slate-400">
                Dispatcher
              </label>
              <Select
                className="w-full"
                value={scenarioDispatcher}
                onChange={(e) => setScenarioDispatcher(e.target.value)}
              >
                {DISPATCHER_OPTIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              {scenarioType === "disable_truck" && (
                <>
                  <label className="mb-1 block text-[11px] text-slate-400">
                    Truck to disable
                  </label>
                  <Select
                    className="w-full"
                    value={disabledTruck}
                    onChange={(e) => setDisabledTruck(e.target.value)}
                  >
                    {TRUCK_IDS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                </>
              )}
              {scenarioType === "block_route" && (
                <>
                  <label className="mb-1 block text-[11px] text-slate-400">
                    Route to block
                  </label>
                  <Select
                    className="w-full"
                    value={blockedRoute}
                    onChange={(e) => setBlockedRoute(e.target.value)}
                  >
                    {ROUTE_IDS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </Select>
                </>
              )}
              {scenarioType === "reduce_speed" && (
                <>
                  <label className="mb-1 block text-[11px] text-slate-400">
                    Truck
                  </label>
                  <Select
                    className="w-full"
                    value={reducedSpeedTruck}
                    onChange={(e) => setReducedSpeedTruck(e.target.value)}
                  >
                    {TRUCK_IDS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                  <label className="mb-1 mt-2 block text-[11px] text-slate-400">
                    New speed: {reducedSpeedValue} km/h
                  </label>
                  <Slider
                    min={1}
                    max={20}
                    step={1}
                    value={reducedSpeedValue}
                    onChange={(e) =>
                      setReducedSpeedValue(parseFloat(e.target.value))
                    }
                  />
                </>
              )}
              {scenarioType === "increase_load" && (
                <>
                  <label className="mb-1 block text-[11px] text-slate-400">
                    Shovel
                  </label>
                  <Select
                    className="w-full"
                    value={increasedLoadShovel}
                    onChange={(e) => setIncreasedLoadShovel(e.target.value)}
                  >
                    {SHOVEL_IDS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </Select>
                  <label className="mb-1 mt-2 block text-[11px] text-slate-400">
                    Load cycle time: {increasedLoadValue} min
                  </label>
                  <Slider
                    min={1}
                    max={10}
                    step={0.5}
                    value={increasedLoadValue}
                    onChange={(e) =>
                      setIncreasedLoadValue(parseFloat(e.target.value))
                    }
                  />
                </>
              )}
            </div>

            <div className="flex items-end">
              <Button
                variant="primary"
                className="w-full"
                disabled={runScenario.isPending}
                onClick={runWhatIf}
              >
                Run what-if scenario
              </Button>
            </div>
          </div>

          {runScenario.data && (
            <div>
              <div className="mb-2 text-xs font-bold uppercase text-sky-400">
                Comparison: Baseline vs Optimized vs What-if
              </div>
              <Table>
                <THead>
                  <TR>
                    <TH>KPI</TH>
                    <TH>Baseline (Naive)</TH>
                    <TH>Optimized (Smart)</TH>
                    <TH>What-if</TH>
                  </TR>
                </THead>
                <TBody>
                  <TR>
                    <TD>Tons produced</TD>
                    <TD>{baselineKpi?.produced_tons.toFixed(2) ?? "No data"}</TD>
                    <TD>{optimizedKpi?.produced_tons.toFixed(2) ?? "No data"}</TD>
                    <TD>{runScenario.data.produced_tons.toFixed(2)}</TD>
                  </TR>
                  <TR>
                    <TD>Completed trips</TD>
                    <TD>{baselineKpi?.completed_trips ?? "No data"}</TD>
                    <TD>{optimizedKpi?.completed_trips ?? "No data"}</TD>
                    <TD>{runScenario.data.completed_trips}</TD>
                  </TR>
                  <TR>
                    <TD>Total fuel (L)</TD>
                    <TD>{baselineKpi?.total_fuel.toFixed(2) ?? "No data"}</TD>
                    <TD>{optimizedKpi?.total_fuel.toFixed(2) ?? "No data"}</TD>
                    <TD>{runScenario.data.total_fuel.toFixed(2)}</TD>
                  </TR>
                  <TR>
                    <TD>Avg cycle time (min)</TD>
                    <TD>{baselineKpi?.avg_cycle_time.toFixed(2) ?? "No data"}</TD>
                    <TD>{optimizedKpi?.avg_cycle_time.toFixed(2) ?? "No data"}</TD>
                    <TD>{runScenario.data.average_cycle_time.toFixed(2)}</TD>
                  </TR>
                  <TR>
                    <TD>Idle time (h)</TD>
                    <TD>{baselineKpi?.truck_idle_time.toFixed(2) ?? "No data"}</TD>
                    <TD>{optimizedKpi?.truck_idle_time.toFixed(2) ?? "No data"}</TD>
                    <TD>{runScenario.data.idle_time.toFixed(2)}</TD>
                  </TR>
                </TBody>
              </Table>
              <div className="mt-2 rounded border border-slate-800 bg-slate-900/60 p-2 text-[11px] text-slate-400">
                Scenario parameters:{" "}
                {JSON.stringify(runScenario.data.scenario_details)} · Dispatcher:{" "}
                {runScenario.data.dispatcher}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
