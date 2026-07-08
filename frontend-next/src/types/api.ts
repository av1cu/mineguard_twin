// TypeScript mirrors of backend/schemas.py Pydantic models.
// Keep in sync manually with backend/schemas.py -- do not modify the backend.

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type EquipmentStatus =
  | "init"
  | "moving"
  | "loading"
  | "unload"
  | "stopped"
  | string;

export type RouteStatus = "active" | "blocked" | string;

export type EventStatus = "new" | "resolved" | string;

export interface EventResponse {
  event_id: string;
  event_time: string;
  source_module: string;
  event_type: string;
  risk_level: RiskLevel;
  risk_score: number;
  equipment_id: string | null;
  driver_id: string | null;
  route_id: string | null;
  section_id: string | null;
  description: string | null;
  recommendation: string | null;
  evidence_path: string | null;
  status: EventStatus;
}

export interface EventStatusUpdate {
  status: string;
}

export interface EquipmentStateResponse {
  equipment_id: string;
  equipment_type: string;
  current_route: string | null;
  current_position_x: number | null;
  current_position_y: number | null;
  speed: number | null;
  status: EquipmentStatus | null;
  driver_id: string | null;
  risk_level: RiskLevel;
  fatigue_score: number;
}

export interface RouteResponse {
  route_id: string;
  route_name: string;
  from_point: string | null;
  to_point: string | null;
  distance_km: number;
  status: RouteStatus;
  risk_level: RiskLevel;
  blocked_reason: string | null;
}

export interface RouteBlockRequest {
  blocked_reason: string;
}

export interface KPIResponse {
  run_id: string;
  dispatcher_name: string;
  completed_trips: number;
  produced_tons: number;
  avg_cycle_time: number;
  truck_idle_time: number;
  total_fuel: number;
  fuel_per_ton: number;
  safety_events_count: number;
}

export interface SimulationStateResponse {
  is_running: boolean;
  current_tick: number;
  max_ticks: number;
  dispatcher: string;
  run_id: string;
  speed_rate: number;
  trucks: EquipmentStateResponse[];
  routes: RouteResponse[];
}

// Recommendation shape varies slightly across two backend implementations,
// so most fields are optional. Handle defensively in the UI.
export interface RecommendationEffects {
  expected_cycle_time_change?: string | number | null;
  expected_fuel_change?: string | number | null;
  expected_productivity_change?: string | number | null;
}

export interface RecommendationResponse {
  id: string;
  category?: string | null;
  event_type?: string | null;
  title?: string | null;
  risk_level?: RiskLevel | null;
  equipment_id?: string | null;
  route_id?: string | null;
  description: string;
  recommendation?: string | null;
  evidence_path?: string | null;
  effects?: RecommendationEffects | null;
}

export interface PredictiveRiskResponse {
  equipment1: string;
  equipment2: string;
  risk_score: number;
  predicted_time: string;
  recommendation: string;
}

export interface ScenarioRunRequest {
  dispatcher: string;
  disabled_truck?: string | null;
  blocked_route?: string | null;
  reduced_speed_truck?: string | null;
  reduced_speed_value?: number | null;
  increased_load_shovel?: string | null;
  increased_load_value?: number | null;
}

export interface ScenarioRunResponse {
  dispatcher: string;
  scenario_details: Record<string, unknown>;
  produced_tons: number;
  completed_trips: number;
  total_fuel: number;
  average_cycle_time: number;
  idle_time: number;
}

// --- Driver fatigue CV (mirrors backend/api.py POST /api/driver/stream_frame) ---

export type DriverEyeState = "OPEN" | "CLOSED" | "PARTIALLY CLOSED" | "N/A";

export interface DriverStreamFrameRequest {
  image: string;
  equipment_id: string;
  calibrate: boolean;
}

export interface DriverStreamFrameResponse {
  success: boolean;
  error?: string;
  image?: string;
  state?: DriverEyeState;
  ear_l?: number;
  ear_r?: number;
  mar?: number;
  is_yawning?: boolean;
  smoothed_ear?: number;
  perclos?: number;
  ear_open?: number;
  threshold_open?: number;
  threshold_closed?: number;
  fatigue_triggered?: boolean;
  is_distracted?: boolean;
  gaze_label?: string;
}
