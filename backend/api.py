from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import sys

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_connection, init_db
from backend.schemas import (
    EventCreate, EventResponse, EventStatusUpdate,
    EquipmentStateResponse, EquipmentStateUpdate,
    RouteResponse, RouteBlockRequest, KPIResponse
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

# Global Simulation Control State
sim_state = {
    "is_running": False,
    "current_tick": 0,
    "dispatcher": "NaiveDispatcher",
    "run_id": "",
    "max_ticks": 200
}

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
def start_simulation(dispatcher: str = "NaiveDispatcher"):
    global sim_state
    sim_state["is_running"] = True
    sim_state["current_tick"] = 0
    sim_state["dispatcher"] = dispatcher
    sim_state["run_id"] = f"RUN-{uuid.uuid4().hex[:6].upper()}"
    
    # Reset equipment status to idle/moving default states
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE equipment_state SET risk_level = 'low', fatigue_score = 0")
    cursor.execute("UPDATE routes SET status = 'active', risk_level = 'low', blocked_reason = ''")
    conn.commit()
    conn.close()
    
    return {
        "status": "started",
        "run_id": sim_state["run_id"],
        "dispatcher": dispatcher
    }

@app.post("/api/simulation/stop")
def stop_simulation():
    global sim_state
    sim_state["is_running"] = False
    return {"status": "stopped", "run_id": sim_state["run_id"]}

@app.get("/api/simulation/state")
def get_simulation_state():
    global sim_state
    # If simulation is running, we increment ticks and update states
    if sim_state["is_running"]:
        sim_state["current_tick"] += 1
        if sim_state["current_tick"] >= sim_state["max_ticks"]:
            sim_state["is_running"] = False
            
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
            "fatigue_triggered": False
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
    
    if result.face_landmarks:
        face_landmarks = result.face_landmarks[0]
        ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
        ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
        ear_avg = (ear_l + ear_r) / 2.0
        
        mar = calculate_mar(face_landmarks, MOUTH_INDICES)
        if mar > 0.5:
            is_yawning = True
            
        if calibrate:
            session["ear_open"] = ear_avg
            
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

        
        if perclos >= 25.0:
            if not session["fatigue_triggered"]:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO events (timestamp, event_type, equipment_id, severity, description, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (datetime.utcnow().isoformat(), "driver_fatigue", equipment_id, "critical", f"Водитель уставший! (PERCLOS: {perclos:.1f}%)", "active")
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
        "fatigue_triggered": session["fatigue_triggered"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
