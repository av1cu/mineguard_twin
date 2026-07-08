from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class EventCreate(BaseModel):
    source_module: str
    event_type: str
    risk_level: str
    risk_score: int
    equipment_id: Optional[str] = None
    driver_id: Optional[str] = None
    route_id: Optional[str] = None
    section_id: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    evidence_path: Optional[str] = None

class EventResponse(BaseModel):
    event_id: str
    event_time: str
    source_module: str
    event_type: str
    risk_level: str
    risk_score: int
    equipment_id: Optional[str]
    driver_id: Optional[str]
    route_id: Optional[str]
    section_id: Optional[str]
    description: Optional[str]
    recommendation: Optional[str]
    evidence_path: Optional[str]
    status: str

class EventStatusUpdate(BaseModel):
    status: str

class EquipmentStateResponse(BaseModel):
    equipment_id: str
    equipment_type: str
    current_route: Optional[str]
    current_position_x: Optional[float]
    current_position_y: Optional[float]
    speed: Optional[float]
    status: Optional[str]
    driver_id: Optional[str]
    risk_level: str
    fatigue_score: int

class EquipmentStateUpdate(BaseModel):
    current_route: Optional[str] = None
    current_position_x: Optional[float] = None
    current_position_y: Optional[float] = None
    speed: Optional[float] = None
    status: Optional[str] = None
    driver_id: Optional[str] = None
    risk_level: Optional[str] = None
    fatigue_score: Optional[int] = None

class RouteResponse(BaseModel):
    route_id: str
    route_name: str
    from_point: Optional[str]
    to_point: Optional[str]
    distance_km: float
    status: str
    risk_level: str
    blocked_reason: Optional[str]

class RouteBlockRequest(BaseModel):
    blocked_reason: str

class KPIResponse(BaseModel):
    run_id: str
    dispatcher_name: str
    completed_trips: int
    produced_tons: float
    avg_cycle_time: float
    truck_idle_time: float
    total_fuel: float
    fuel_per_ton: float
    safety_events_count: int
