# MineGuard Twin — SCADA Console (Next.js frontend)

A Next.js 14 (App Router, TypeScript) frontend that replaces the previous
Streamlit UI. It is a pure consumer of the existing FastAPI backend
(`backend/api.py`, `backend/schemas.py`) — no backend code was modified.

## Quick start (local dev)

```bash
cd frontend-next
npm install
npm run dev
```

The app expects the backend to be reachable at the URL configured by
`NEXT_PUBLIC_BACKEND_URL` (see below). Open http://localhost:3000 — it
redirects to `/dashboard`.

### Environment variables

| Variable                     | Default                 | Notes                                             |
|-------------------------------|--------------------------|----------------------------------------------------|
| `NEXT_PUBLIC_BACKEND_URL`      | `http://localhost:8000` | Base URL for the FastAPI backend. Read client-side, so it must be reachable from the *browser*, not just from inside a container. |

Create a `.env.local` file to override it locally:

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Docker usage

```bash
docker compose up --build
```

This builds the `backend` (FastAPI, port 8000) and `frontend` (this Next.js
app, port 3000) services. Since `NEXT_PUBLIC_BACKEND_URL` is inlined into the
client bundle at build time and used directly by the browser, it is set to
`http://localhost:8000` (not the in-network `backend` hostname) — the browser
runs on the host machine, outside the Docker network.

## Project structure

```
frontend-next/
├── src/
│   ├── app/                # App Router pages (see list below) + layout/providers
│   ├── components/         # Presentational + feature components
│   │   └── ui/             # Hand-rolled minimal Tailwind primitives (button, card, badge, dialog, select, slider, tabs, table, tooltip)
│   ├── hooks/queries.ts     # All React Query hooks + mutations (polling, cache invalidation)
│   ├── lib/api.ts           # Pure fetch layer — one function per backend endpoint, no React
│   ├── lib/utils.ts         # cn() class merge helper, formatNumber()
│   ├── store/mapStore.ts    # Zustand store: selection, pan/zoom, dispatcher/speed UI state, map display toggles
│   └── types/api.ts         # TypeScript mirrors of backend/schemas.py (no `any`)
├── Dockerfile               # Multi-stage build → next start on port 3000
└── package.json
```

## Pages

- `/dashboard` — Live SCADA console: interactive mine map (react-konva),
  KPI cards, alarms, recommendations, predictive risk panel, simulation
  controls, equipment telemetry list. Port of `01_dashboard.py` + `mine_map.py`.
- `/simulation` — Baseline vs optimized run buttons, KPI comparison
  table + bar charts, what-if scenario builder. Port of `02_simulation.py`.
- `/analytics` — Deeper trend charts across all recorded KPI runs (fuel
  efficiency, safety events, cycle/idle time trends). New page, not present
  in the original Streamlit app (see decisions below).
- `/events` — Filterable event log (module / risk level) + detail dialog.
  Port of `05_events.py`.
- `/equipment` — Full equipment/truck roster table.
- `/routes` — Road network table with block/unblock actions.
- `/settings` — Backend URL, polling intervals, map display toggles,
  dispatcher default (read-only informational page).

## Mine map (SCADA canvas)

`src/components/MineCanvas.tsx` dynamically imports `MineCanvasInner.tsx`
(`ssr: false`, since Konva requires a browser environment). Key behaviors,
ported from `frontend/mine_map.py`:

- Draggable `Stage` for panning, mouse-wheel zoom clamped to `[0.4, 5.0]`.
- Truck positions are interpolated every animation frame
  (`requestAnimationFrame`) toward the latest polled target position using
  LERP factor `0.08`, matching the original canvas implementation.
- All per-frame updates mutate Konva node refs directly
  (`node.position()`, `node.rotation()`, ring radius, predictive-line
  points) — **no React state is set on every animation tick**. React state
  (`dataVersion`) is only bumped when new telemetry is polled (every 500 ms),
  which re-renders truck colors/status/labels at a much lower frequency.
- Click-to-select a truck highlights it with crosshair rings and syncs
  with the Zustand store, so the sidebar `EquipmentList` / `TruckHUD` reflect
  the same selection.
- Hover shows a floating HUD with telemetry (id, driver, status, speed,
  risk, fatigue, coordinates).
- Dashed amber lines are drawn between truck pairs returned by
  `/api/predictive_risks`, tracking their interpolated (not raw) positions.

## Data flow / architecture

- `src/lib/api.ts` is pure `fetch` wrappers — no React, no hooks. Easy to
  test/reuse.
- `src/hooks/queries.ts` wraps every endpoint in a React Query hook.
  `useSimulationState()` polls every 500 ms; events/recommendations/predictive
  risks poll a bit slower (1–2 s) since they change less often; KPIs poll
  every 2 s. Mutations invalidate the relevant query keys on success.
- `src/store/mapStore.ts` (Zustand) holds UI-only state that several
  components need without prop-drilling: selected truck id, map pan/zoom,
  map display toggles, and the currently-selected dispatcher/speed for the
  simulation control panel.

## Ambiguous-spec decisions

- **Recommendations shape**: the spec noted the recommendation response
  shape "varies slightly across two implementations in the backend." All
  fields except `id` and `description` are typed optional in
  `RecommendationResponse`, and the UI falls back gracefully (e.g. shows
  `event_type` if `title` is absent).
- **Evidence images**: the original Streamlit page read evidence JPEGs
  directly off the local filesystem (`Image.open(evidence_path)`), which
  only works when the frontend and backend share a filesystem. Since the
  Next.js frontend runs in the browser and the API doesn't expose an
  evidence-file endpoint, the Events detail dialog shows a placeholder
  message instead of attempting to load the image.
- **Analytics page**: not present in the original Streamlit app (which only
  had Dashboard/Simulation/Events/CV pages). Since the task asked for an
  Analytics page with "deeper KPI charts / trends," and `KPIResponse` has no
  timestamp field, trends are plotted against run index (`#1`, `#2`, …,
  labelled with dispatcher name) rather than wall-clock time.
- **Static map layout**: mine site coordinates (`DemoChargingSite`,
  `Shovel-01..03`, `Dump-01..02`) are hardcoded per the spec, matching
  `simulation/configs/demo_mine.json`. Roads are drawn from the live
  `/api/simulation/state` → `routes` array (`from_point`/`to_point` looked
  up against the static site table) when available, falling back to the
  fully-connected static road network if no route data has loaded yet.
- **shadcn/ui**: the CLI requires network access to fetch component source
  from the shadcn registry, which was unreliable in this sandboxed build
  environment. Per the task's fallback instruction, all "shadcn-style"
  primitives (button, card, badge, dialog, select, slider, tabs, table,
  tooltip) were hand-rolled directly with Tailwind under `src/components/ui/`
  instead.
- **Next.js/swc version pin**: `next@14.2.34`/`14.2.35` do not currently
  publish a matching `@next/swc-linux-x64-gnu` native binary on the npm
  registry (confirmed via `npm view`), which crashes the build with a
  `SIGBUS` when the mismatched cached binary is loaded. The project is
  pinned to `next@14.2.33` / `eslint-config-next@14.2.33`, the latest patch
  version with a verified matching native build in this environment.

## Verification performed

- `npx tsc --noEmit` — passes with zero errors.
- `npm run lint` — zero warnings/errors.
- `npm run build` — production build succeeds (`✓ Compiled successfully`,
  all 12 routes prerendered as static content).
