"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Stage, Layer, Line, Circle, Group, Rect, Text } from "react-konva";
import type Konva from "konva";
import type { KonvaEventObject } from "konva/lib/Node";
import { useMapStore } from "@/store/mapStore";
import {
  useEquipment,
  usePredictiveRisks,
  useSimulationState,
} from "@/hooks/queries";
import type { EquipmentStateResponse, RiskLevel } from "@/types/api";

interface SitePoint {
  name: string;
  x: number;
  y: number;
}

const CHARGING_SITE: SitePoint = { name: "DemoChargingSite", x: 0, y: 0 };
const LOAD_SITES: SitePoint[] = [
  { name: "Shovel-01", x: 10, y: 20 },
  { name: "Shovel-02", x: -15, y: 30 },
  { name: "Shovel-03", x: 5, y: -25 },
];
const DUMP_SITES: SitePoint[] = [
  { name: "Dump-01", x: 40, y: 0 },
  { name: "Dump-02", x: -40, y: -10 },
];

const POINTS: Record<string, SitePoint> = {
  [CHARGING_SITE.name]: CHARGING_SITE,
  ...Object.fromEntries(LOAD_SITES.map((s) => [s.name, s])),
  ...Object.fromEntries(DUMP_SITES.map((s) => [s.name, s])),
};

const SCALE = 8.5;
const LERP_FACTOR = 0.08;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 5.0;

interface TruckKinematic {
  equipment_id: string;
  tx: number;
  ty: number;
  rx: number;
  ry: number;
  angle: number;
  status: string;
  risk_level: RiskLevel;
  speed: number | null;
  driver_id: string | null;
  fatigue_score: number;
  current_route: string | null;
}

function riskColor(risk: string): string {
  if (risk === "medium") return "#f59e0b";
  if (risk === "high" || risk === "critical") return "#ef4444";
  return "#10b981";
}

function statusSymbol(status: string): string {
  if (status === "stopped") return "STOP";
  if (status === "loading") return "LOAD";
  if (status === "unload") return "DUMP";
  return "";
}

interface HoverInfo {
  type: "truck" | "shovel" | "dump" | "charge";
  name: string;
  truck?: TruckKinematic;
}

export default function MineCanvasInner() {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const layerRef = useRef<Konva.Layer>(null);

  const truckGroupRefs = useRef<Map<string, Konva.Group>>(new Map());
  const pulseRingRefs = useRef<Map<string, Konva.Circle>>(new Map());
  const predLineRefs = useRef<Map<string, Konva.Line>>(new Map());
  const predDotRefs = useRef<Map<string, Konva.Circle>>(new Map());
  const truckDataRef = useRef<Map<string, TruckKinematic>>(new Map());
  const rafRef = useRef<number | null>(null);

  const [size, setSize] = useState({ width: 800, height: 600 });
  const [truckIds, setTruckIds] = useState<string[]>([]);
  const [dataVersion, setDataVersion] = useState(0);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const zoom = useMapStore((s) => s.zoom);
  const setZoom = useMapStore((s) => s.setZoom);
  const panX = useMapStore((s) => s.panX);
  const panY = useMapStore((s) => s.panY);
  const setPan = useMapStore((s) => s.setPan);
  const selectedEquipmentId = useMapStore((s) => s.selectedEquipmentId);
  const toggleSelectedEquipmentId = useMapStore(
    (s) => s.toggleSelectedEquipmentId
  );
  const displaySettings = useMapStore((s) => s.displaySettings);

  const { data: simState } = useSimulationState();
  const { data: equipment } = useEquipment();
  const { data: predictiveRisks } = usePredictiveRisks();

  const trucks: EquipmentStateResponse[] = useMemo(
    () => simState?.trucks ?? equipment ?? [],
    [simState, equipment]
  );
  const routes = simState?.routes ?? [];

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      setSize({ width: el.clientWidth, height: el.clientHeight });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const toCanvasCoords = useCallback(
    (x: number, y: number) => {
      const cx = size.width / 2;
      const cy = size.height / 2;
      return { x: cx + x * SCALE, y: cy - y * SCALE };
    },
    [size]
  );

  const toRealWorldCoords = useCallback(
    (mx: number, my: number) => {
      const cx = size.width / 2;
      const cy = size.height / 2;
      // Account for stage pan (panX/panY) and zoom applied around center.
      const localX = (mx - panX - cx) / zoom + cx;
      const localY = (my - panY - cy) / zoom + cy;
      return {
        x: (localX - cx) / SCALE,
        y: (cy - localY) / SCALE,
      };
    },
    [size, panX, panY, zoom]
  );

  // Sync polled truck data into kinematic refs (target positions), and bump
  // dataVersion so colors/status/labels re-render — but NOT the per-frame loop.
  useEffect(() => {
    const map = truckDataRef.current;
    const currentIds = new Set(map.keys());
    const nextIds = new Set<string>();

    trucks.forEach((t) => {
      nextIds.add(t.equipment_id);
      const tx = t.current_position_x ?? 0;
      const ty = t.current_position_y ?? 0;
      const existing = map.get(t.equipment_id);
      if (!existing) {
        map.set(t.equipment_id, {
          equipment_id: t.equipment_id,
          tx,
          ty,
          rx: tx,
          ry: ty,
          angle: 0,
          status: t.status ?? "moving",
          risk_level: t.risk_level,
          speed: t.speed,
          driver_id: t.driver_id,
          fatigue_score: t.fatigue_score,
          current_route: t.current_route,
        });
      } else {
        existing.tx = tx;
        existing.ty = ty;
        existing.status = t.status ?? "moving";
        existing.risk_level = t.risk_level;
        existing.speed = t.speed;
        existing.driver_id = t.driver_id;
        existing.fatigue_score = t.fatigue_score;
        existing.current_route = t.current_route;
      }
    });

    // Remove stale trucks
    currentIds.forEach((id) => {
      if (!nextIds.has(id)) {
        map.delete(id);
        truckGroupRefs.current.delete(id);
        pulseRingRefs.current.delete(id);
      }
    });

    const sortedNext = Array.from(nextIds).sort();
    const sortedCurrent = truckIds.slice().sort();
    const changed =
      sortedNext.length !== sortedCurrent.length ||
      sortedNext.some((id, i) => id !== sortedCurrent[i]);
    if (changed) {
      setTruckIds(Array.from(nextIds));
    }
    setDataVersion((v) => v + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trucks]);

  // 60fps animation loop: LERP positions + rotation + pulse rings + predictive
  // lines, all mutated imperatively on Konva nodes (no React state per frame).
  useEffect(() => {
    function animate() {
      const map = truckDataRef.current;
      map.forEach((t, id) => {
        const dx = t.tx - t.rx;
        const dy = t.ty - t.ry;
        t.rx += dx * LERP_FACTOR;
        t.ry += dy * LERP_FACTOR;

        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > 0.03) {
          t.angle = Math.atan2(dy, -dx);
        }

        const node = truckGroupRefs.current.get(id);
        if (node) {
          const pos = toCanvasCoords(t.rx, t.ry);
          node.position(pos);
          node.rotation((t.angle * 180) / Math.PI);
        }

        const ring = pulseRingRefs.current.get(id);
        if (ring) {
          if (t.risk_level === "high" || t.risk_level === "critical") {
            const pulse = Math.abs(Math.sin(Date.now() / 150)) * 6;
            ring.radius(15 + pulse);
            ring.visible(true);
          } else {
            ring.visible(false);
          }
        }
      });

      // Predictive risk lines follow interpolated truck positions
      (predictiveRisks ?? []).forEach((r) => {
        const key = `${r.equipment1}__${r.equipment2}`;
        const t1 = map.get(r.equipment1);
        const t2 = map.get(r.equipment2);
        const line = predLineRefs.current.get(key);
        const dot = predDotRefs.current.get(key);
        if (t1 && t2 && line && dot) {
          const p1 = toCanvasCoords(t1.rx, t1.ry);
          const p2 = toCanvasCoords(t2.rx, t2.ry);
          line.points([p1.x, p1.y, p2.x, p2.y]);
          dot.position({ x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 });
        }
      });

      layerRef.current?.batchDraw();
      rafRef.current = requestAnimationFrame(animate);
    }
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [toCanvasCoords, predictiveRisks]);

  const handleWheel = useCallback(
    (e: KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();
      const zoomFactor = 1.15;
      const next =
        e.evt.deltaY < 0 ? zoom * zoomFactor : zoom / zoomFactor;
      setZoom(Math.max(MIN_ZOOM, Math.min(next, MAX_ZOOM)));
    },
    [zoom, setZoom]
  );

  const handleDragEnd = useCallback(
    (e: KonvaEventObject<DragEvent>) => {
      setPan(e.target.x(), e.target.y());
    },
    [setPan]
  );

  const handleMouseMove = useCallback(
    (e: KonvaEventObject<MouseEvent>) => {
      const stage = e.target.getStage();
      const pointer = stage?.getPointerPosition();
      if (!pointer) return;
      setMousePos({ x: pointer.x, y: pointer.y });
      const real = toRealWorldCoords(pointer.x, pointer.y);

      let found: HoverInfo | null = null;
      truckDataRef.current.forEach((t) => {
        if (found) return;
        const dist = Math.hypot(real.x - t.rx, real.y - t.ry);
        if (dist < 3.0) {
          found = { type: "truck", name: t.equipment_id, truck: { ...t } };
        }
      });
      if (!found) {
        LOAD_SITES.forEach((s) => {
          if (found) return;
          const dist = Math.hypot(real.x - s.x, real.y - s.y);
          if (dist < 3.5) found = { type: "shovel", name: s.name };
        });
      }
      if (!found) {
        DUMP_SITES.forEach((s) => {
          if (found) return;
          const dist = Math.hypot(real.x - s.x, real.y - s.y);
          if (dist < 3.5) found = { type: "dump", name: s.name };
        });
      }
      if (!found) {
        const dist = Math.hypot(
          real.x - CHARGING_SITE.x,
          real.y - CHARGING_SITE.y
        );
        if (dist < 3.5) found = { type: "charge", name: CHARGING_SITE.name };
      }

      setHover((prev) => {
        if (!found && !prev) return prev;
        if (
          found &&
          prev &&
          prev.type === found.type &&
          prev.name === found.name &&
          prev.truck?.status === found.truck?.status &&
          prev.truck?.risk_level === found.truck?.risk_level
        ) {
          return { ...found };
        }
        return found;
      });
    },
    [toRealWorldCoords]
  );

  const handleClickTruck = useCallback(
    (id: string) => {
      toggleSelectedEquipmentId(id);
    },
    [toggleSelectedEquipmentId]
  );

  const chargePos = toCanvasCoords(CHARGING_SITE.x, CHARGING_SITE.y);

  return (
    <div ref={containerRef} className="relative h-full w-full bg-[#070a13]">
      <Stage
        ref={stageRef}
        width={size.width}
        height={size.height}
        draggable
        x={panX}
        y={panY}
        scaleX={zoom}
        scaleY={zoom}
        onWheel={handleWheel}
        onDragEnd={handleDragEnd}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHover(null)}
      >
        <Layer ref={layerRef}>
          {/* Grid */}
          {displaySettings.showGrid &&
            Array.from({ length: 40 }).map((_, i) => {
              const gridSize = 35;
              const offset = (i - 20) * gridSize;
              return (
                <Line
                  key={`grid-v-${i}`}
                  points={[offset + size.width / 2, -2000, offset + size.width / 2, 2000]}
                  stroke="rgba(31,41,55,0.3)"
                  strokeWidth={1}
                />
              );
            })}

          {/* Roads */}
          {routes.map((r) => {
            const from = r.from_point ? POINTS[r.from_point] : undefined;
            const to = r.to_point ? POINTS[r.to_point] : undefined;
            if (!from || !to) return null;
            const p1 = toCanvasCoords(from.x, from.y);
            const p2 = toCanvasCoords(to.x, to.y);
            const blocked = r.status === "blocked";
            return (
              <Group key={r.route_id}>
                <Line
                  points={[p1.x, p1.y, p2.x, p2.y]}
                  stroke="#1e293b"
                  strokeWidth={16}
                  lineCap="round"
                />
                <Line
                  points={[p1.x, p1.y, p2.x, p2.y]}
                  stroke={blocked ? "#ef4444" : "#334155"}
                  strokeWidth={blocked ? 4 : 2}
                  dash={[8, 8]}
                />
              </Group>
            );
          })}
          {/* Fallback static roads if no route data yet */}
          {routes.length === 0 &&
            LOAD_SITES.flatMap((ls) => {
              const lsPos = toCanvasCoords(ls.x, ls.y);
              const lines = [
                <Line
                  key={`road-charge-${ls.name}`}
                  points={[chargePos.x, chargePos.y, lsPos.x, lsPos.y]}
                  stroke="#1e293b"
                  strokeWidth={16}
                  lineCap="round"
                />,
              ];
              DUMP_SITES.forEach((ds) => {
                const dsPos = toCanvasCoords(ds.x, ds.y);
                lines.push(
                  <Line
                    key={`road-${ls.name}-${ds.name}`}
                    points={[lsPos.x, lsPos.y, dsPos.x, dsPos.y]}
                    stroke="#1e293b"
                    strokeWidth={16}
                    lineCap="round"
                  />
                );
              });
              return lines;
            })}

          {/* Sites */}
          <Group>
            <Circle x={chargePos.x} y={chargePos.y} radius={14} fill="#1d4ed8" stroke="#3b82f6" strokeWidth={2} />
            <Text
              x={chargePos.x - 60}
              y={chargePos.y + 18}
              width={120}
              align="center"
              text={CHARGING_SITE.name}
              fontSize={9}
              fontStyle="bold"
              fill="#3b82f6"
            />
          </Group>
          {LOAD_SITES.map((ls) => {
            const pos = toCanvasCoords(ls.x, ls.y);
            return (
              <Group key={ls.name}>
                <Circle x={pos.x} y={pos.y} radius={12} fill="#a16207" stroke="#eab308" strokeWidth={2} />
                <Text
                  x={pos.x - 60}
                  y={pos.y - 32}
                  width={120}
                  align="center"
                  text={ls.name}
                  fontSize={9}
                  fontStyle="bold"
                  fill="#eab308"
                />
              </Group>
            );
          })}
          {DUMP_SITES.map((ds) => {
            const pos = toCanvasCoords(ds.x, ds.y);
            return (
              <Group key={ds.name}>
                <Circle x={pos.x} y={pos.y} radius={13} fill="#44403c" stroke="#78716c" strokeWidth={2} />
                <Text
                  x={pos.x - 60}
                  y={pos.y - 32}
                  width={120}
                  align="center"
                  text={ds.name}
                  fontSize={9}
                  fontStyle="bold"
                  fill="#a8a29e"
                />
              </Group>
            );
          })}

          {/* Predictive risk lines (dashed) */}
          {displaySettings.showPredictiveLines &&
            (predictiveRisks ?? []).map((r) => {
              const key = `${r.equipment1}__${r.equipment2}`;
              return (
                <Group key={key}>
                  <Line
                    ref={(node) => {
                      if (node) predLineRefs.current.set(key, node);
                      else predLineRefs.current.delete(key);
                    }}
                    points={[0, 0, 0, 0]}
                    stroke="#f59e0b"
                    strokeWidth={1.5}
                    dash={[4, 4]}
                  />
                  <Circle
                    ref={(node) => {
                      if (node) predDotRefs.current.set(key, node);
                      else predDotRefs.current.delete(key);
                    }}
                    radius={8}
                    fill="#f59e0b"
                  />
                </Group>
              );
            })}

          {/* Trucks */}
          {truckIds.map((id) => {
            const t = truckDataRef.current.get(id);
            if (!t) return null;
            const color = riskColor(t.risk_level);
            const isSelected = selectedEquipmentId === id;
            const symbol = statusSymbol(t.status);
            void dataVersion; // re-render trigger for color/label/status changes
            return (
              <Group
                key={id}
                ref={(node) => {
                  if (node) truckGroupRefs.current.set(id, node);
                  else truckGroupRefs.current.delete(id);
                }}
                onClick={() => handleClickTruck(id)}
                onTap={() => handleClickTruck(id)}
              >
                <Circle
                  ref={(node) => {
                    if (node) pulseRingRefs.current.set(id, node);
                    else pulseRingRefs.current.delete(id);
                  }}
                  radius={15}
                  stroke="rgba(239,68,68,0.4)"
                  strokeWidth={2}
                  visible={false}
                />
                {isSelected && (
                  <>
                    <Circle radius={22} stroke="#0ea5e9" strokeWidth={1.5} />
                    <Line points={[-28, 0, -18, 0]} stroke="#0ea5e9" strokeWidth={1.5} />
                    <Line points={[18, 0, 28, 0]} stroke="#0ea5e9" strokeWidth={1.5} />
                    <Line points={[0, -28, 0, -18]} stroke="#0ea5e9" strokeWidth={1.5} />
                    <Line points={[0, 18, 0, 28]} stroke="#0ea5e9" strokeWidth={1.5} />
                  </>
                )}
                {/* Wheels */}
                <Rect x={-10} y={-8} width={4} height={2} fill="#111827" />
                <Rect x={3} y={-8} width={4} height={2} fill="#111827" />
                <Rect x={-10} y={6} width={4} height={2} fill="#111827" />
                <Rect x={3} y={6} width={4} height={2} fill="#111827" />
                {/* Chassis */}
                <Rect
                  x={-12}
                  y={-6}
                  width={17}
                  height={12}
                  cornerRadius={1.5}
                  fill={color}
                  stroke="#ffffff"
                  strokeWidth={1}
                />
                {/* Cabin */}
                <Rect x={5} y={-5} width={5} height={10} fill="#1e293b" />
                <Rect x={7} y={-3} width={2} height={6} fill="#38bdf8" />
                {/* Label */}
                <Text
                  x={-40}
                  y={-30}
                  width={80}
                  align="center"
                  text={id}
                  fontSize={9}
                  fontStyle="bold"
                  fill="#ffffff"
                />
                {symbol && (
                  <Text
                    x={-40}
                    y={16}
                    width={80}
                    align="center"
                    text={symbol}
                    fontSize={9}
                    fontStyle="bold"
                    fill="#fbbf24"
                  />
                )}
              </Group>
            );
          })}
        </Layer>
      </Stage>

      {/* Hover HUD */}
      {hover && (
        <div
          className="pointer-events-none absolute w-64 rounded-md border border-sky-600 bg-slate-900/90 p-3 shadow-xl backdrop-blur"
          style={{ top: 16, left: 16 }}
        >
          {hover.type === "truck" && hover.truck ? (
            <>
              <div className="mb-1.5 border-b border-slate-700 pb-1 text-xs font-bold text-sky-400">
                Truck: {hover.truck.equipment_id}
              </div>
              <HudRow label="Driver" value={hover.truck.driver_id ?? "—"} />
              <HudRow
                label="Status"
                value={hover.truck.status.toUpperCase()}
                color={riskColor(hover.truck.risk_level)}
              />
              <HudRow label="Speed" value={`${hover.truck.speed ?? 0} km/h`} />
              <HudRow
                label="Risk"
                value={hover.truck.risk_level.toUpperCase()}
                color={riskColor(hover.truck.risk_level)}
              />
              <HudRow label="Fatigue" value={`${hover.truck.fatigue_score}%`} />
              <HudRow
                label="Coords"
                value={`${hover.truck.rx.toFixed(1)}, ${hover.truck.ry.toFixed(1)}`}
              />
            </>
          ) : (
            <div className="text-xs font-bold text-sky-400">{hover.name}</div>
          )}
        </div>
      )}

      <div className="pointer-events-none absolute bottom-4 left-4 rounded border border-slate-700 bg-slate-900/70 px-2.5 py-1.5 text-[10px] text-slate-400">
        Drag to pan · Scroll to zoom · Click a truck to select
      </div>
      <div className="pointer-events-none absolute bottom-0 right-0" style={{ display: "none" }}>
        {mousePos.x}
      </div>
    </div>
  );
}

function HudRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="mb-1 flex justify-between text-[11px]">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold" style={color ? { color } : { color: "#f8fafc" }}>
        {value}
      </span>
    </div>
  );
}
