import json
import math
import random
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_connection
from simulation.energy_layer import EnergyLayer
from simulation.safety_layer import SafetyLayer

class MineSimulation:
    def __init__(self, config_path: str, dispatcher_name: str = "NaiveDispatcher"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        self.dispatcher_name = dispatcher_name
        self.energy_layer = EnergyLayer(self.config.get("energy_profile"))
        self.safety_layer = SafetyLayer(proximity_threshold=5.0)
        
        # Load sites coordinates
        self.points = {
            "DemoChargingSite": [0.0, 0.0],
            "Shovel-01": [10.0, 20.0],
            "Shovel-02": [-15.0, 30.0],
            "Shovel-03": [5.0, -25.0],
            "Dump-01": [40.0, 0.0],
            "Dump-02": [-40.0, -10.0]
        }
        
        # Define routes and distance
        self.routes_config = {
            "ROUTE-01": {"from": "Shovel-01", "to": "Dump-01", "distance": 3.2},
            "ROUTE-02": {"from": "Shovel-02", "to": "Dump-01", "distance": 4.5},
            "ROUTE-03": {"from": "Shovel-03", "to": "Dump-02", "distance": 2.8},
            "ROUTE-04": {"from": "Shovel-01", "to": "Dump-02", "distance": 5.1}
        }
        
        self.trucks = [
            {"id": "TRUCK-01", "type": "OfficalTruck", "capacity": 77, "speed": 35.0, "status": "init", "route": "ROUTE-01", "progress": 0.0},
            {"id": "TRUCK-02", "type": "CLTruck", "capacity": 35, "speed": 30.0, "status": "init", "route": "ROUTE-02", "progress": 0.0},
            {"id": "TRUCK-03", "type": "XHTruck", "capacity": 55, "speed": 28.0, "status": "init", "route": "ROUTE-03", "progress": 0.0},
            {"id": "TRUCK-04", "type": "OfficalTruck", "capacity": 77, "speed": 35.0, "status": "init", "route": "ROUTE-01", "progress": 0.0},
            {"id": "TRUCK-05", "type": "CLTruck", "capacity": 35, "speed": 30.0, "status": "init", "route": "ROUTE-02", "progress": 0.0}
        ]
        
        # KPI Accumulators
        self.completed_trips = 0
        self.produced_tons = 0.0
        self.total_fuel = 0.0
        self.idle_fuel = 0.0
        self.safety_events = 0
        self.truck_idle_time = 0.0
        
        self.init_db_state()

    def init_db_state(self):
        conn = get_connection()
        cursor = conn.cursor()
        for t in self.trucks:
            p_start = self.points["DemoChargingSite"]
            cursor.execute("""
            INSERT OR REPLACE INTO equipment_state 
            (equipment_id, equipment_type, current_route, current_position_x, current_position_y, speed, status, driver_id, risk_level, fatigue_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (t["id"], t["type"], t["route"], p_start[0], p_start[1], 0.0, t["status"], f"DRIVER-{t['id'][-2:]}", "low", 0))
        conn.commit()
        conn.close()

    def step(self):
        # Fetch current blockages and driver states from DB
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT route_id, status, risk_level FROM routes")
        routes_db = {row["route_id"]: {"status": row["status"], "risk_level": row["risk_level"]} for row in cursor.fetchall()}
        
        cursor.execute("SELECT equipment_id, risk_level, fatigue_score FROM equipment_state")
        trucks_db = {row["equipment_id"]: {"risk_level": row["risk_level"], "fatigue_score": row["fatigue_score"]} for row in cursor.fetchall()}
        
        conn.close()

        updated_trucks = []
        for t in self.trucks:
            t_id = t["id"]
            db_info = trucks_db.get(t_id, {"risk_level": "low", "fatigue_score": 0})
            fatigue_score = db_info["fatigue_score"]
            risk_level = db_info["risk_level"]
            
            # --- Energy Aware Safety Dispatcher (Smart Dispatcher) Logic ---
            route_id = t["route"]
            route_info = routes_db.get(route_id, {"status": "active", "risk_level": "low"})
            
            # If critical risk (e.g. driver asleep), stop the truck
            if risk_level == "critical":
                t["status"] = "stopped"
                t["speed"] = 0.0
                # Fuel consumed while stopped with engine running (idle)
                fuel = self.energy_layer.calculate_fuel("stopped", 0.0, 1.0/60.0)
                self.total_fuel += fuel
                self.idle_fuel += fuel
                self.truck_idle_time += 1.0/60.0
                
                # Write back state
                updated_trucks.append(self._get_truck_pos_dict(t, fatigue_score, risk_level))
                continue
                
            # If path is blocked and we are optimized, reroute!
            if self.dispatcher_name == "SmartDispatcher" and route_info["status"] == "blocked":
                # Find alternative route
                if route_id == "ROUTE-01":
                    t["route"] = "ROUTE-04" # Use backup
                    route_id = "ROUTE-04"
                elif route_id == "ROUTE-02":
                    t["route"] = "ROUTE-01" # Reroute to Shovel 01 path
                    route_id = "ROUTE-01"
                    
            # Move truck
            route_config = self.routes_config.get(route_id, {"from": "DemoChargingSite", "to": "Dump-01", "distance": 3.0})
            total_dist = route_config["distance"]
            
            # Simulating status transitions
            if t["status"] in ["init", "back"]:
                # Moving empty towards shovel
                speed = t["speed"]
                t["progress"] += (speed / 3600.0) # Speed in km/h to km/minute (since 1 step = 1 minute)
                fuel = self.energy_layer.calculate_fuel("moving_empty", speed / 3600.0, 0.0)
                self.total_fuel += fuel
                
                if t["progress"] >= total_dist:
                    t["status"] = "loading"
                    t["progress"] = 0.0
                    
            elif t["status"] == "loading":
                # Idling at shovel
                fuel = self.energy_layer.calculate_fuel("loading", 0.0, 1.0/60.0)
                self.total_fuel += fuel
                self.idle_fuel += fuel
                self.truck_idle_time += 1.0/60.0
                
                if random.random() < 0.3: # 30% chance to finish loading each step
                    t["status"] = "haul"
                    t["progress"] = 0.0
                    
            elif t["status"] == "haul":
                # Moving loaded towards dump
                speed = t["speed"] * 0.8 # Slower when loaded
                t["progress"] += (speed / 3600.0)
                fuel = self.energy_layer.calculate_fuel("moving_loaded", speed / 3600.0, 0.0)
                self.total_fuel += fuel
                
                # If using baseline dispatcher and path is blocked, get stuck!
                if self.dispatcher_name == "NaiveDispatcher" and route_info["status"] == "blocked" and t["progress"] >= total_dist * 0.5:
                    t["status"] = "idle" # stuck in traffic
                    t["speed_current"] = 0.0
                    # Log safety proximity violation (optional)
                    
                if t["progress"] >= total_dist:
                    t["status"] = "unload"
                    t["progress"] = 0.0
                    
            elif t["status"] == "unload":
                # Idling at dump
                fuel = self.energy_layer.calculate_fuel("unload", 0.0, 1.0/60.0)
                self.total_fuel += fuel
                self.idle_fuel += fuel
                self.truck_idle_time += 1.0/60.0
                
                if random.random() < 0.5: # 50% chance to finish unloading
                    t["status"] = "back"
                    t["progress"] = 0.0
                    self.completed_trips += 1
                    self.produced_tons += t["capacity"]
                    
            elif t["status"] == "idle": # stuck in traffic/blocked route
                fuel = self.energy_layer.calculate_fuel("idle", 0.0, 1.0/60.0)
                self.total_fuel += fuel
                self.idle_fuel += fuel
                self.truck_idle_time += 1.0/60.0
                # If baseline dispatcher, we stay stuck unless route unblocks
                if route_info["status"] == "active":
                    t["status"] = "haul"

            # Determine coordinates based on route and progress
            p_from = self.points[route_config["from"]]
            p_to = self.points[route_config["to"]]
            
            ratio = min(t["progress"] / total_dist, 1.0)
            x = p_from[0] + (p_to[0] - p_from[0]) * ratio
            y = p_from[1] + (p_to[1] - p_from[1]) * ratio
            
            t["x"] = x
            t["y"] = y
            
            updated_trucks.append({
                "equipment_id": t["id"],
                "equipment_type": t["type"],
                "current_route": t["route"],
                "current_position_x": x,
                "current_position_y": y,
                "speed": t["speed"] if t["status"] in ["init", "back", "haul"] else 0.0,
                "status": t["status"],
                "driver_id": f"DRIVER-{t['id'][-2:]}",
                "risk_level": risk_level,
                "fatigue_score": fatigue_score
            })
            
        # Detect proximities
        violations = self.safety_layer.detect_dangerous_proximity(updated_trucks)
        self.safety_events += len(violations)
        
        # Save updated states to SQLite
        conn = get_connection()
        cursor = conn.cursor()
        for ut in updated_trucks:
            cursor.execute("""
            UPDATE equipment_state
            SET current_route = ?, current_position_x = ?, current_position_y = ?,
                speed = ?, status = ?
            WHERE equipment_id = ?
            """, (
                ut["current_route"], ut["current_position_x"], ut["current_position_y"],
                ut["speed"], ut["status"], ut["equipment_id"]
            ))
        conn.commit()
        conn.close()
        
        return updated_trucks

    def _get_truck_pos_dict(self, t, fatigue_score, risk_level):
        route_config = self.routes_config.get(t["route"], {"from": "DemoChargingSite", "to": "Dump-01", "distance": 3.0})
        p_from = self.points[route_config["from"]]
        ratio = min(t["progress"] / route_config["distance"], 1.0)
        x = p_from[0] + (self.points[route_config["to"]][0] - p_from[0]) * ratio
        y = p_from[1] + (self.points[route_config["to"]][1] - p_from[1]) * ratio
        return {
            "equipment_id": t["id"],
            "equipment_type": t["type"],
            "current_route": t["route"],
            "current_position_x": x,
            "current_position_y": y,
            "speed": 0.0,
            "status": t["status"],
            "driver_id": f"DRIVER-{t['id'][-2:]}",
            "risk_level": risk_level,
            "fatigue_score": fatigue_score
        }

    def save_run_kpis(self, run_id: str):
        conn = get_connection()
        cursor = conn.cursor()
        
        avg_cycle = (self.truck_idle_time * 60 + 20) / max(self.completed_trips, 1) # simple calculation
        fuel_per_ton = self.total_fuel / max(self.produced_tons, 1.0)
        
        cursor.execute("""
        INSERT OR REPLACE INTO simulation_kpi (
            run_id, dispatcher_name, completed_trips, produced_tons, avg_cycle_time,
            truck_idle_time, total_fuel, fuel_per_ton, safety_events_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, self.dispatcher_name, self.completed_trips, self.produced_tons, avg_cycle,
            self.truck_idle_time, self.total_fuel, fuel_per_ton, self.safety_events
        ))
        
        conn.commit()
        conn.close()
        print(f"Simulation KPI saved for run {run_id} ({self.dispatcher_name})")
