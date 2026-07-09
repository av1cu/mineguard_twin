from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import sys

logger = logging.getLogger(__name__)

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_connection, init_db
from backend.schemas import (
    EventCreate, EventResponse, EventStatusUpdate,
    EquipmentStateResponse, EquipmentStateUpdate,
    RouteResponse, RouteBlockRequest, KPIResponse
)

# --- AI Agent layer (additive, does not modify existing architecture) ---
from agent.agent_core import run_agent
from agent.memory import get_conversation_memory
from agent.prompts import get_system_prompt, SHIFT_REPORT_INSTRUCTIONS, WHATIF_INSTRUCTIONS
from agent.schemas import (
    AgentChatRequest, AgentChatResponse, WhatIfRequest, ShiftReportResponse, ProposedAction
)

app = FastAPI(title="MineGuard Twin Backend API", version="1.0.0")

# Enable CORS for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "null"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# NOTE: FastAPI/Starlette gotcha - CORS headers are added by CORSMiddleware
# while the response travels back *through* it, but an unhandled exception
# is normally caught by an outer error-handling layer that sits *outside*
# CORSMiddleware, so the resulting 500 response has no CORS headers at all.
# Browsers then misreport this as "blocked by CORS policy" even though the
# real problem is a server-side 500 (e.g. the agent's LLM call failing).
# Registering an explicit exception handler routes the error response back
# through CORSMiddleware like any other response, fixing the symptom; it
# does not change behavior for any of the existing endpoints.
@app.exception_handler(Exception)
async def _cors_safe_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception in %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})


# Global Simulation Control State
sim_state = {
    "is_running": False,
    "current_tick": 0,
    "dispatcher": "NaiveDispatcher",
    "run_id": "",
    "max_ticks": 120
}

import threading
import time

class SimulationRunner:
    def __init__(self):
        self.sim = None
        self.is_running = False
        self.current_tick = 0
        self.max_ticks = 120
        self.dispatcher = "NaiveDispatcher"
        self.run_id = ""
        self.speed_rate = 1.0
        self.thread = None
        self.lock = threading.Lock()
        
    def start(self, dispatcher: str = "NaiveDispatcher", speed_rate: float = 1.0):
        with self.lock:
            self.dispatcher = dispatcher
            self.speed_rate = speed_rate
            
            if not self.sim:
                from simulation.openmines_adapter import MineSimulation
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "simulation", "configs", "demo_mine.json")
                self.sim = MineSimulation(config_path, dispatcher_name=dispatcher)
                self.run_id = f"RUN-{uuid.uuid4().hex[:6].upper()}"
                self.current_tick = 0
                
            self.is_running = True
            
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                
    def pause(self):
        with self.lock:
            self.is_running = False
            
    def reset(self):
        with self.lock:
            self.is_running = False
            self.sim = None
            self.current_tick = 0
            self.run_id = ""
            
            # Reset SQLite state
            from backend.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE equipment_state SET risk_level = 'low', fatigue_score = 0, status = 'init'")
            cursor.execute("UPDATE routes SET status = 'active', risk_level = 'low', blocked_reason = ''")
            conn.commit()
            conn.close()
            
    def set_speed(self, speed_rate: float):
        with self.lock:
            self.speed_rate = speed_rate
            
    def _run_loop(self):
        while True:
            with self.lock:
                if not self.is_running:
                    break
                if self.current_tick >= self.max_ticks:
                    self.is_running = False
                    if self.sim:
                        try:
                            self.sim.save_run_kpis(self.run_id)
                        except Exception as e:
                            print("Error saving KPIs in simulation runner:", e)
                    break
                
                try:
                    self.sim.step()
                except Exception as e:
                    print("Error during simulation step in background:", e)
                    self.is_running = False
                    break
                
                self.current_tick += 1
                delay = 1.0 / self.speed_rate
                
            time.sleep(delay)

runner = SimulationRunner()

# Ensure database is initialized on startup
@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "MineGuard Twin Backend API"}

# --- Events Endpoints ---

@app.post("/api/events", response_model=EventResponse)
def create_event(event: EventCreate):
    conn = get_connection()
    cursor = conn.cursor()
    
    event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
    event_time = datetime.now().isoformat()
    status = "new"
    
    cursor.execute("""
    INSERT INTO events (
        event_id, event_time, source_module, event_type, risk_level, risk_score,
        equipment_id, driver_id, route_id, section_id, description, recommendation,
        evidence_path, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id, event_time, event.source_module, event.event_type, event.risk_level, event.risk_score,
        event.equipment_id, event.driver_id, event.route_id, event.section_id, event.description,
        event.recommendation, event.evidence_path, status
    ))
    
    # Side effects: if event is driver_fatigue, update driver's equipment state risk level
    if event.event_type == "driver_fatigue" and event.equipment_id:
        # Determine risk level based on fatigue score
        new_risk = "medium"
        if event.risk_level == "critical":
            new_risk = "critical"
        elif event.risk_level == "high":
            new_risk = "high"
            
        cursor.execute("""
        UPDATE equipment_state 
        SET risk_level = ?, fatigue_score = ? 
        WHERE equipment_id = ?
        """, (new_risk, event.risk_score, event.equipment_id))
        
    # Side effects: if event is slope_anomaly, update route state risk level and route block status if critical
    if event.event_type == "slope_anomaly" and event.route_id:
        new_risk = event.risk_level
        cursor.execute("""
        UPDATE routes 
        SET risk_level = ?
        WHERE route_id = ?
        """, (new_risk, event.route_id))
        
        # If high/critical, auto-block for baseline or recommend blocking
        if event.risk_level in ["high", "critical"]:
            cursor.execute("""
            UPDATE routes 
            SET status = 'blocked', blocked_reason = ? 
            WHERE route_id = ?
            """, (event.description, event.route_id))

    conn.commit()
    
    cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row)

@app.get("/api/events", response_model=List[EventResponse])
def get_events(limit: int = 100, source_module: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    if source_module:
        cursor.execute("SELECT * FROM events WHERE source_module = ? ORDER BY event_time DESC LIMIT ?", (source_module, limit))
    else:
        cursor.execute("SELECT * FROM events ORDER BY event_time DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/events/{event_id}", response_model=EventResponse)
def get_event(event_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return dict(row)

@app.post("/api/events/{event_id}/status", response_model=EventResponse)
def update_event_status(event_id: str, payload: EventStatusUpdate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET status = ? WHERE event_id = ?", (payload.status, event_id))
    conn.commit()
    cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return dict(row)

# --- Simulation Endpoints ---

@app.post("/api/simulation/start")
def start_simulation(dispatcher: str = "NaiveDispatcher", speed: float = 1.0):
    runner.start(dispatcher=dispatcher, speed_rate=speed)
    return {
        "status": "started",
        "run_id": runner.run_id,
        "dispatcher": dispatcher
    }

@app.post("/api/simulation/stop")
def stop_simulation():
    runner.pause()
    return {"status": "stopped", "run_id": runner.run_id}

@app.post("/api/simulation/reset")
def reset_simulation():
    runner.reset()
    return {"status": "reset"}

@app.post("/api/simulation/speed")
def set_simulation_speed(speed: float):
    runner.set_speed(speed)
    return {"status": "speed_updated", "speed": speed}

@app.get("/api/simulation/state")
def get_simulation_state():
    global sim_state
    sim_state["is_running"] = runner.is_running
    sim_state["current_tick"] = runner.current_tick
    sim_state["max_ticks"] = runner.max_ticks
    sim_state["dispatcher"] = runner.dispatcher
    sim_state["run_id"] = runner.run_id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM equipment_state")
    trucks = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM routes")
    routes = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "is_running": sim_state["is_running"],
        "current_tick": sim_state["current_tick"],
        "max_ticks": sim_state["max_ticks"],
        "dispatcher": sim_state["dispatcher"],
        "run_id": sim_state["run_id"],
        "speed_rate": runner.speed_rate,
        "trucks": trucks,
        "routes": routes
    }

@app.get("/api/simulation/kpi", response_model=List[KPIResponse])
def get_simulation_kpi():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_kpi")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/simulation/kpi")
def add_simulation_kpi(kpi: KPIResponse):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO simulation_kpi (
        run_id, dispatcher_name, completed_trips, produced_tons, avg_cycle_time,
        truck_idle_time, total_fuel, fuel_per_ton, safety_events_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        kpi.run_id, kpi.dispatcher_name, kpi.completed_trips, kpi.produced_tons, kpi.avg_cycle_time,
        kpi.truck_idle_time, kpi.total_fuel, kpi.fuel_per_ton, kpi.safety_events_count
    ))
    conn.commit()
    conn.close()
    return {"status": "saved"}

# --- Slope and Road CV Endpoints ---

@app.post("/api/slope/analyze")
def analyze_slope(section_id: str, image_url: Optional[str] = None):
    # Simulated CV slope inspection endpoint
    # Calculates a risk score and fires an event if risk > 30
    import random
    
    # Mocking different levels of risk based on random chance or section
    risk_score = random.randint(10, 95)
    risk_level = "low"
    if risk_score > 80:
        risk_level = "critical"
    elif risk_score > 60:
        risk_level = "high"
    elif risk_score > 30:
        risk_level = "medium"
        
    detected_objects = []
    if risk_score > 30:
        if random.choice([True, False]): detected_objects.append("crack")
        if random.choice([True, False]): detected_objects.append("rockfall")
        if not detected_objects: detected_objects.append("road_damage")
        
    description = f"Slope CV inspection for section {section_id}. Detected: {', '.join(detected_objects) if detected_objects else 'no anomalies'}."
    recommendation = "Block route and inspect section" if risk_level in ["high", "critical"] else "Routine monitoring"
    
    # Map section to Route ID for demo simplicity
    route_id = "ROUTE-02" if "NORTH" in section_id.upper() or "02" in section_id else "ROUTE-01"
    
    event_data = EventCreate(
        source_module="slope_cv",
        event_type="slope_anomaly",
        risk_level=risk_level,
        risk_score=risk_score,
        route_id=route_id,
        section_id=section_id,
        description=description,
        recommendation=recommendation,
        evidence_path=f"data/evidence/slope_{section_id.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )
    
    event_res = create_event(event_data)
    return event_res

# --- Driver CV Endpoints ---

@app.post("/api/driver/analyze")
def analyze_driver(equipment_id: str, fatigue_score: int, detected_signals: List[str]):
    # Endpoint to submit driver CV analysis results
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT driver_id FROM equipment_state WHERE equipment_id = ?", (equipment_id,))
    row = cursor.fetchone()
    conn.close()
    
    driver_id = row["driver_id"] if row else "DRIVER-UNKNOWN"
    
    risk_level = "low"
    if fatigue_score > 80:
        risk_level = "critical"
    elif fatigue_score > 50:
        risk_level = "high"
    elif fatigue_score > 25:
        risk_level = "medium"
        
    description = f"Driver CV monitor for {equipment_id}. Signals: {', '.join(detected_signals)}."
    recommendation = "Stop truck immediately" if risk_level in ["high", "critical"] else "Dispatch driver warning alert"
    
    event_data = EventCreate(
        source_module="driver_cv",
        event_type="driver_fatigue",
        risk_level=risk_level,
        risk_score=fatigue_score,
        equipment_id=equipment_id,
        driver_id=driver_id,
        description=description,
        recommendation=recommendation,
        evidence_path=f"data/evidence/driver_{equipment_id.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )
    
    event_res = create_event(event_data)
    return event_res

# --- Equipment and Routes Endpoints ---

@app.get("/api/equipment", response_model=List[EquipmentStateResponse])
def get_equipment():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_state")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/routes", response_model=List[RouteResponse])
def get_routes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM routes")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/routes/{route_id}/block", response_model=RouteResponse)
def block_route(route_id: str, payload: RouteBlockRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE routes 
    SET status = 'blocked', blocked_reason = ?, risk_level = 'high' 
    WHERE route_id = ?
    """, (payload.blocked_reason, route_id))
    conn.commit()
    cursor.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Route not found")
    return dict(row)

@app.post("/api/routes/{route_id}/unblock", response_model=RouteResponse)
def unblock_route(route_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE routes 
    SET status = 'active', blocked_reason = '', risk_level = 'low' 
    WHERE route_id = ?
    """, (route_id,))
    conn.commit()
    cursor.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Route not found")
    return dict(row)

@app.get("/api/recommendations")
def get_recommendations():
    # Return recommendations based on current high-risk events or blocked routes
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE status = 'new' AND risk_level IN ('high', 'critical')")
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    recommendations = []
    for e in events:
        recommendations.append({
            "id": e["event_id"],
            "event_type": e["event_type"],
            "risk_level": e["risk_level"],
            "equipment_id": e["equipment_id"],
            "route_id": e["route_id"],
            "description": e["description"],
            "recommendation": e["recommendation"],
            "evidence_path": e["evidence_path"]
        })
    return recommendations

@app.post("/api/recommendations/{id}/accept")
def accept_recommendation(id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET status = 'accepted' WHERE event_id = ?", (id,))
    
    # Side effects: if it's a driver fatigue alert, set truck risk level to low (assuming stopped/resolved)
    cursor.execute("SELECT * FROM events WHERE event_id = ?", (id,))
    e = cursor.fetchone()
    if e and e["event_type"] == "driver_fatigue":
        cursor.execute("UPDATE equipment_state SET risk_level = 'low', fatigue_score = 0 WHERE equipment_id = ?", (e["equipment_id"],))
        
    conn.commit()
    conn.close()
    return {"status": "accepted", "id": id}

# --- Live Driver Webcam Stream ---
import base64
import cv2
import numpy as np

live_sessions = {}
landmarker_instance = None

def get_backend_landmarker():
    global landmarker_instance
    if landmarker_instance is None:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cv_driver", "models", "face_landmarker.task")
            if not os.path.exists(model_path):
                import urllib.request
                url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                urllib.request.urlretrieve(url, model_path)
                
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1
            )
            landmarker_instance = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Error initializing backend landmarker: {e}")
    return landmarker_instance

L_EYE_INDICES = [362, 385, 387, 263, 373, 380]
R_EYE_INDICES = [33, 160, 158, 133, 153, 144]

def calculate_single_ear(landmarks, eye_indices) -> float:
    p = [np.array([landmarks[idx].x, landmarks[idx].y]) for idx in eye_indices]
    d_v1 = np.linalg.norm(p[1] - p[5])
    d_v2 = np.linalg.norm(p[2] - p[4])
    d_h = np.linalg.norm(p[0] - p[3])
    return float((d_v1 + d_v2) / (2.0 * d_h + 1e-6))

MOUTH_INDICES = [78, 308, 13, 14]

def calculate_mar(landmarks, indices) -> float:
    p_left = np.array([landmarks[indices[0]].x, landmarks[indices[0]].y])
    p_right = np.array([landmarks[indices[1]].x, landmarks[indices[1]].y])
    p_top = np.array([landmarks[indices[2]].x, landmarks[indices[2]].y])
    p_bottom = np.array([landmarks[indices[3]].x, landmarks[indices[3]].y])
    
    d_v = np.linalg.norm(p_top - p_bottom)
    d_h = np.linalg.norm(p_left - p_right)
    return float(d_v / (d_h + 1e-6))

@app.post("/api/driver/stream_frame")
def stream_driver_frame(payload: dict):
    img_data = payload.get("image")
    equipment_id = payload.get("equipment_id", "TRUCK-04")
    calibrate = payload.get("calibrate", False)
    
    if not img_data:
        return {"success": False, "error": "No image data"}
        
    if "," in img_data:
        img_data = img_data.split(",")[1]
        
    try:
        img_bytes = base64.b64decode(img_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return {"success": False, "error": f"Decode error: {e}"}
        
    if frame is None:
        return {"success": False, "error": "Frame is empty"}
        
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    if equipment_id not in live_sessions:
        live_sessions[equipment_id] = {
            "ear_open": 0.28,
            "ear_window": [],
            "perclos_window": [],
            "fatigue_triggered": False,
            "distraction_triggered": False,
            "distraction_frames": 0,
            "yaw_base": 1.0,
            "pitch_base": 1.0
        }
    session = live_sessions[equipment_id]
    
    landmarker = get_backend_landmarker()
    if landmarker is None:
        return {"success": False, "error": "MediaPipe Landmarker failed to load"}
        
    try:
        import mediapipe as mp
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = landmarker.detect(mp_image)
    except Exception as e:
        return {"success": False, "error": f"Inference failed: {e}"}
        
    state_label = "N/A"
    ear_l = 0.0
    ear_r = 0.0
    mar = 0.0
    smoothed_ear = 0.0
    perclos = 0.0
    is_yawning = False
    is_distracted = False
    gaze_label = "AHEAD"
    
    if result.face_landmarks:
        face_landmarks = result.face_landmarks[0]
        ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
        ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
        ear_avg = (ear_l + ear_r) / 2.0
        
        mar = calculate_mar(face_landmarks, MOUTH_INDICES)
        if mar > 0.5:
            is_yawning = True
            

        ear_open = session["ear_open"]
        threshold_open = ear_open * 0.82
        threshold_closed = ear_open * 0.74
        
        session["ear_window"].append(ear_avg)
        if len(session["ear_window"]) > 8:
            session["ear_window"].pop(0)
        smoothed_ear = float(np.mean(session["ear_window"]))
        
        is_closed = False
        if smoothed_ear >= threshold_open:
            state_label = "OPEN"
        elif smoothed_ear <= threshold_closed:
            state_label = "CLOSED"
            is_closed = True
        else:
            state_label = "PARTIALLY CLOSED"
            
        session["perclos_window"].append(1 if is_closed else 0)
        if len(session["perclos_window"]) > 80:
            session["perclos_window"].pop(0)
        perclos = (sum(session["perclos_window"]) / len(session["perclos_window"])) * 100.0

        # Gaze tracking (distraction detection)
        p_nose = np.array([face_landmarks[1].x, face_landmarks[1].y])
        p_eye_l = np.mean([np.array([face_landmarks[idx].x, face_landmarks[idx].y]) for idx in L_EYE_INDICES], axis=0)
        p_eye_r = np.mean([np.array([face_landmarks[idx].x, face_landmarks[idx].y]) for idx in R_EYE_INDICES], axis=0)
        dist_l = np.linalg.norm(p_nose - p_eye_l)
        dist_r = np.linalg.norm(p_nose - p_eye_r)
        head_yaw_ratio = dist_l / (dist_r + 1e-6)
        
        p_forehead = np.array([face_landmarks[10].x, face_landmarks[10].y])
        p_chin = np.array([face_landmarks[152].x, face_landmarks[152].y])
        dist_top = np.linalg.norm(p_forehead - p_nose)
        dist_bottom = np.linalg.norm(p_chin - p_nose)
        head_pitch_ratio = dist_top / (dist_bottom + 1e-6)
        
        # Save baseline during calibration
        if calibrate:
            session["ear_open"] = ear_avg
            session["yaw_base"] = head_yaw_ratio
            session["pitch_base"] = head_pitch_ratio
            
        # Calculate relative deviation from baseline
        yaw_dev = head_yaw_ratio / (session["yaw_base"] + 1e-6)
        pitch_dev = head_pitch_ratio / (session["pitch_base"] + 1e-6)
        
        has_iris = len(face_landmarks) > 473
        gaze_ratio_l = 1.0
        gaze_ratio_r = 1.0
        
        if has_iris:
            p_pupil_l = np.array([face_landmarks[468].x, face_landmarks[468].y])
            p_pupil_r = np.array([face_landmarks[473].x, face_landmarks[473].y])
            p_corner_l_inner = np.array([face_landmarks[362].x, face_landmarks[362].y])
            p_corner_l_outer = np.array([face_landmarks[263].x, face_landmarks[263].y])
            p_corner_r_inner = np.array([face_landmarks[133].x, face_landmarks[133].y])
            p_corner_r_outer = np.array([face_landmarks[33].x, face_landmarks[33].y])
            
            gaze_ratio_l = np.linalg.norm(p_pupil_l - p_corner_l_outer) / (np.linalg.norm(p_pupil_l - p_corner_l_inner) + 1e-6)
            gaze_ratio_r = np.linalg.norm(p_pupil_r - p_corner_r_outer) / (np.linalg.norm(p_pupil_r - p_corner_r_inner) + 1e-6)
            
        if yaw_dev > 1.25 or yaw_dev < 0.8:
            is_distracted = True
            gaze_label = "LOOKING SIDEWAYS"
        elif pitch_dev > 1.3 or pitch_dev < 0.75:
            is_distracted = True
            gaze_label = "LOOKING UP/DOWN"
        elif has_iris and (gaze_ratio_l > 1.65 or gaze_ratio_l < 0.6 or gaze_ratio_r > 1.65 or gaze_ratio_r < 0.6):
            is_distracted = True
            gaze_label = "LOOKING SIDEWAYS"
            
        if is_distracted:
            session["distraction_frames"] += 1
            if session["distraction_frames"] >= 15:
                if not session["distraction_triggered"]:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
                        cursor.execute(
                            """
                            INSERT INTO events (
                                event_id, event_time, source_module, event_type, risk_level, risk_score,
                                equipment_id, driver_id, description, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (event_id, datetime.now().isoformat(), "driver_monitoring", "driver_distraction", "high", 80, equipment_id, f"DRIVER-{equipment_id[-2:]}", f"Водитель отвлекся! (Направление: {gaze_label})", "active")
                        )
                        cursor.execute(
                            "UPDATE equipment_state SET risk_level = 'high' WHERE equipment_id = ?",
                            (equipment_id,)
                        )
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print("Error logging distraction event to DB:", e)
                    session["distraction_triggered"] = True
        else:
            session["distraction_frames"] = 0
            if session["distraction_triggered"]:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE equipment_state SET risk_level = 'low' WHERE equipment_id = ?",
                        (equipment_id,)
                    )
                    conn.commit()
                    conn.close()
                except:
                    pass
                session["distraction_triggered"] = False
        
        if perclos >= 25.0:
            if not session["fatigue_triggered"]:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
                    cursor.execute(
                        """
                        INSERT INTO events (
                            event_id, event_time, source_module, event_type, risk_level, risk_score,
                            equipment_id, driver_id, description, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (event_id, datetime.now().isoformat(), "driver_monitoring", "driver_fatigue", "critical", int(perclos), equipment_id, f"DRIVER-{equipment_id[-2:]}", f"Водитель уставший! (PERCLOS: {perclos:.1f}%)", "active")
                    )
                    cursor.execute(
                        "UPDATE equipment_state SET risk_level = 'critical', fatigue_score = ? WHERE equipment_id = ?",
                        (int(perclos), equipment_id)
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print("Error logging fatigue event to DB:", e)
                session["fatigue_triggered"] = True
        elif perclos < 10.0:
            session["fatigue_triggered"] = False
            
        for lm in face_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 1, (0, 255, 0), -1)
            
        for idx in L_EYE_INDICES + R_EYE_INDICES:
            lm = face_landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)
            
        for idx in MOUTH_INDICES:
            lm = face_landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 3, (255, 0, 0), -1)
            
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        encoded_image = base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        return {"success": False, "error": f"Encode error: {e}"}
        
    return {
        "success": True,
        "image": f"data:image/jpeg;base64,{encoded_image}",
        "state": state_label,
        "ear_l": ear_l,
        "ear_r": ear_r,
        "mar": mar,
        "is_yawning": is_yawning,
        "smoothed_ear": smoothed_ear,
        "perclos": perclos,
        "ear_open": session["ear_open"],
        "threshold_open": session["ear_open"] * 0.82,
        "threshold_closed": session["ear_open"] * 0.74,
        "fatigue_triggered": session["fatigue_triggered"],
        "is_distracted": is_distracted,
        "gaze_label": gaze_label
    }

from pydantic import BaseModel

class ScenarioRunRequest(BaseModel):
    dispatcher: str = "NaiveDispatcher"
    disabled_truck: Optional[str] = None
    blocked_route: Optional[str] = None
    reduced_speed_truck: Optional[str] = None
    reduced_speed_value: Optional[float] = 5.0
    increased_load_shovel: Optional[str] = None
    increased_load_value: Optional[float] = 5.0

scenario_results = {
    "latest": None
}

@app.post("/api/scenario/run")
def run_scenario(payload: ScenarioRunRequest):
    global scenario_results
    
    scenario = {}
    if payload.disabled_truck:
        scenario["disabled_truck"] = payload.disabled_truck
    if payload.blocked_route:
        scenario["blocked_route"] = payload.blocked_route
    if payload.reduced_speed_truck:
        scenario["reduced_speed_truck"] = payload.reduced_speed_truck
        scenario["reduced_speed_value"] = payload.reduced_speed_value
    if payload.increased_load_shovel:
        scenario["increased_load_shovel"] = payload.increased_load_shovel
        scenario["increased_load_value"] = payload.increased_load_value
        
    from simulation.openmines_adapter import MineSimulation
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "simulation", "configs", "demo_mine.json")
    
    try:
        sim = MineSimulation(config_path, dispatcher_name=payload.dispatcher, scenario=scenario)
        
        # Calculate KPIs
        completed_trips = sim.completed_trips
        produced_tons = sim.produced_tons
        total_fuel = sim.total_fuel
        avg_cycle_time = (sim.truck_idle_time * 60 + 20) / max(completed_trips, 1)
        idle_time = sim.truck_idle_time
        
        res = {
            "dispatcher": payload.dispatcher,
            "scenario_details": scenario,
            "produced_tons": float(produced_tons),
            "completed_trips": int(completed_trips),
            "total_fuel": float(total_fuel),
            "average_cycle_time": float(avg_cycle_time),
            "idle_time": float(idle_time)
        }
        scenario_results["latest"] = res
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scenario simulation: {str(e)}")

@app.get("/api/scenario/result")
def get_scenario_result():
    global scenario_results
    if not scenario_results["latest"]:
        raise HTTPException(status_code=404, detail="No scenario run results found.")
    return scenario_results["latest"]

@app.get("/api/recommendations")
def get_recommendations():
    recs = []
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_state")
    trucks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # 1. Driver fatigue check (fatigue > 80)
    for t in trucks:
        if t["fatigue_score"] >= 80:
            recs.append({
                "id": f"REC-FATIGUE-{t['equipment_id']}",
                "category": "Безопасность (Усталость)",
                "title": f"Замена водителя {t['equipment_id']}",
                "description": f"Уровень усталости водителя {t['driver_id']} составляет {t['fatigue_score']}%. Рекомендуется заменить водителя.",
                "effects": {
                    "expected_cycle_time_change": "-12.0%",
                    "expected_fuel_change": "-5.0%",
                    "expected_productivity_change": "+8.0%"
                }
            })
            
    # 2. Queue check (queue > 5)
    has_long_queue = False
    if runner.sim and runner.dispatcher == "NaiveDispatcher" and runner.current_tick > 10:
        has_long_queue = True
        
    if has_long_queue:
        recs.append({
            "id": "REC-QUEUE-REROUTE",
            "category": "Эффективность (Очередь)",
            "title": "Перенаправление Truck-03 на Route-02",
            "description": "Зафиксирована очередь из 5+ самосвалов на погрузочном узле Shovel-01. Рекомендуется перенаправить Truck-03 на Route-02.",
            "effects": {
                "expected_cycle_time_change": "-18.0%",
                "expected_fuel_change": "-3.0%",
                "expected_productivity_change": "+12.0%"
            }
        })
        
    # 3. Fuel check (fuel consumption > average)
    high_fuel = False
    if runner.sim and runner.sim.total_fuel > 150.0:
        fuel_per_ton = runner.sim.total_fuel / max(runner.sim.produced_tons, 1.0)
        if fuel_per_ton > 1.2:
            high_fuel = True
            
    if high_fuel:
        recs.append({
            "id": "REC-FUEL-ROUTE",
            "category": "Энергоэффективность",
            "title": "Использовать альтернативный маршрут",
            "description": "Расход топлива выше среднего. Рекомендуется использовать альтернативный равнинный маршрут ROUTE-04 для обхода горного склона.",
            "effects": {
                "expected_cycle_time_change": "+5.0%",
                "expected_fuel_change": "-15.0%",
                "expected_productivity_change": "+2.0%"
            }
        })
        
    # 4. Collision check (collision expected)
    has_collision_risk = False
    danger_truck = "Truck-05"
    for t in trucks:
        if t["risk_level"] in ["high", "critical"]:
            has_collision_risk = True
            danger_truck = t["equipment_id"]
            break
            
    if has_collision_risk:
        recs.append({
            "id": "REC-COLLISION-STOP",
            "category": "Безопасность (Столкновение)",
            "title": f"Остановка {danger_truck}",
            "description": f"Ожидается столкновение или опасное сближение из-за отвлечения/микросна. Рекомендуется временно остановить {danger_truck}.",
            "effects": {
                "expected_cycle_time_change": "+1.0%",
                "expected_fuel_change": "0.0%",
                "expected_productivity_change": "0.0%"
            }
        })
        
    return recs

@app.get("/api/predictive_risks")
def get_predictive_risks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_state")
    trucks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    from simulation.predictive_safety import PredictiveSafety
    ps = PredictiveSafety(safe_threshold=8.0)
    
    try:
        risks = ps.analyze_telemetry(trucks, lookahead_seconds=5.0)
        return risks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate predictive risks: {str(e)}")

# --- Equipment manual control (additive; needed so the AI agent's proposed
# actions -- stop / resume equipment -- have a real "Apply" endpoint for the
# dispatcher to click. Dangerous actions are never executed by the agent
# itself, see agent/tools.py propose_* builders). ---

@app.post("/api/equipment/{equipment_id}/stop", response_model=EquipmentStateResponse)
def stop_equipment(equipment_id: str, reason: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE equipment_state SET status = 'stopped' WHERE equipment_id = ?", (equipment_id,))
    conn.commit()
    cursor.execute("SELECT * FROM equipment_state WHERE equipment_id = ?", (equipment_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return dict(row)


@app.post("/api/equipment/{equipment_id}/resume", response_model=EquipmentStateResponse)
def resume_equipment(equipment_id: str, reset_risk: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    if reset_risk:
        cursor.execute(
            "UPDATE equipment_state SET status = 'idle', risk_level = 'low', fatigue_score = 0 WHERE equipment_id = ?",
            (equipment_id,),
        )
    else:
        cursor.execute("UPDATE equipment_state SET status = 'idle' WHERE equipment_id = ?", (equipment_id,))
    conn.commit()
    cursor.execute("SELECT * FROM equipment_state WHERE equipment_id = ?", (equipment_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return dict(row)


# --- AI Agent (Decision Support System) Endpoints -----------------------
# Read-heavy, tool-calling agent built on top of the existing DB/simulation
# layers (see agent/tools.py). It never mutates state directly: any risky
# action it wants is surfaced as `proposed_actions`, and the dispatcher must
# call the explicit apply endpoints above (or the pre-existing routes/block,
# routes/unblock, recommendations/accept) to actually execute it.

@app.post("/api/agent/chat", response_model=AgentChatResponse)
async def agent_chat(payload: AgentChatRequest):
    memory = get_conversation_memory()
    history = memory.get(payload.session_id)

    result = await run_agent(
        system_prompt=get_system_prompt(),
        user_message=payload.message,
        history=history,
    )

    memory.add_turn(payload.session_id, "user", payload.message)
    memory.add_turn(payload.session_id, "assistant", result.answer)

    return AgentChatResponse(
        answer=result.answer,
        proposed_actions=[ProposedAction(**a) for a in result.proposed_actions],
        trace=result.trace,
        session_id=payload.session_id,
    )


@app.post("/api/agent/whatif", response_model=AgentChatResponse)
async def agent_whatif(payload: WhatIfRequest):
    system_prompt = get_system_prompt() + "\n\n" + WHATIF_INSTRUCTIONS
    result = await run_agent(system_prompt=system_prompt, user_message=payload.question)
    return AgentChatResponse(
        answer=result.answer,
        proposed_actions=[ProposedAction(**a) for a in result.proposed_actions],
        trace=result.trace,
        session_id=payload.session_id,
    )


@app.get("/api/agent/shift_report", response_model=ShiftReportResponse)
async def agent_shift_report():
    system_prompt = get_system_prompt() + "\n\n" + SHIFT_REPORT_INSTRUCTIONS
    result = await run_agent(
        system_prompt=system_prompt,
        user_message="Составь отчёт за текущую смену.",
    )
    return ShiftReportResponse(
        report=result.answer,
        generated_at=datetime.now().isoformat(),
        proposed_actions=[ProposedAction(**a) for a in result.proposed_actions],
        trace=result.trace,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
