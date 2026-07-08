import json
import math
import random
import os
import sys
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_connection
from simulation.energy_layer import EnergyLayer
from simulation.safety_layer import SafetyLayer

# Import from openmines external library
from openmines.src.mine import Mine
from openmines.src.truck import Truck
from openmines.src.charging_site import ChargingSite
from openmines.src.load_site import LoadSite, Shovel
from openmines.src.dump_site import DumpSite, Dumper
from openmines.src.road import Road

class MineSimulation:
    def __init__(self, config_path: str, dispatcher_name: str = "NaiveDispatcher"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        self.dispatcher_name = dispatcher_name
        self.energy_layer = EnergyLayer(self.config.get("energy_profile"))
        self.safety_layer = SafetyLayer(proximity_threshold=5.0)
        
        # Grid Coordinates mapping
        self.points = {
            "DemoChargingSite": [0.0, 0.0],
            "Shovel-01": [10.0, 20.0],
            "Shovel-02": [-15.0, 30.0],
            "Shovel-03": [5.0, -25.0],
            "Dump-01": [40.0, 0.0],
            "Dump-02": [-40.0, -10.0]
        }
        
        # Truck mappings from OpenMines to DB
        self.truck_mapping = {
            "OfficalTruck1": "TRUCK-01",
            "CLTruck1": "TRUCK-02",
            "XHTruck1": "TRUCK-03",
            "OfficalTruck2": "TRUCK-04",
            "CLTruck2": "TRUCK-05"
        }
        
        self.last_positions = {}
        
        # KPI accumulators
        self.completed_trips = 0
        self.produced_tons = 0.0
        self.total_fuel = 0.0
        self.idle_fuel = 0.0
        self.safety_events = 0
        self.truck_idle_time = 0.0
        self.current_tick = 0
        
        # 1. Translate our config to OpenMines format
        om_config = self._translate_config()
        
        # 2. Setup and run OpenMines simulation
        self.ticks = self._run_openmines(om_config)
        
        # Initialize DB states
        self.init_db_state()

    def _translate_config(self) -> dict:
        """Converts the project's config style into OpenMines style config."""
        l2d = []
        for ls in self.config["load_site"]:
            row = []
            for ds in self.config["dump_site"]:
                row.append(self._get_route_distance(ls["name"], ds["name"]))
            l2d.append(row)
            
        d2l = []
        for ds in self.config["dump_site"]:
            row = []
            for ls in self.config["load_site"]:
                row.append(self._get_route_distance(ls["name"], ds["name"]))
            d2l.append(row)
            
        c2l = []
        for ls in self.config["load_site"]:
            p1 = self.config["charging_site"]["position"]
            p2 = ls["position"]
            dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) / 10.0
            c2l.append(round(dist, 1))
            
        load_sites = []
        for ls in self.config["load_site"]:
            load_sites.append({
                "name": ls["name"],
                "position": ls["position"],
                "shovels": [
                    {
                        "name": f"{ls['name']}-S1",
                        "tons": 15,
                        "cycle_time": 1.5,
                        "position_offset": [0, 0]
                    }
                ],
                "parkinglot": {
                    "name": f"{ls['name']}-P1",
                    "position_offset": [0, 0]
                }
            })
            
        dump_sites = []
        for ds in self.config["dump_site"]:
            dump_sites.append({
                "name": ds["name"],
                "position": ds["position"],
                "dumpers": [
                    {
                        "name": f"{ds['name']}-D1",
                        "cycle_time": 1.2,
                        "position_offset": [0, 0],
                        "count": 1
                    }
                ],
                "parkinglot": {
                    "name": f"{ds['name']}-P1",
                    "position_offset": [0, 0]
                }
            })
            
        return {
            "mine": {
                "name": self.config["mine"]["name"]
            },
            "sim_time": 120,
            "dispatcher": {
                "type": [self.dispatcher_name]
            },
            "charging_site": self.config["charging_site"],
            "load_sites": load_sites,
            "dump_sites": dump_sites,
            "road": {
                "l2d_road_matrix": l2d,
                "d2l_road_matrix": d2l,
                "charging_to_load_road_matrix": c2l
            }
        }

    def _get_route_distance(self, load_name: str, dump_name: str) -> float:
        pairs = {
            ("Shovel-01", "Dump-01"): 3.2,
            ("Shovel-02", "Dump-01"): 4.5,
            ("Shovel-03", "Dump-02"): 2.8,
            ("Shovel-01", "Dump-02"): 5.1,
        }
        if (load_name, dump_name) in pairs:
            return pairs[(load_name, dump_name)]
        p1 = next(ls["position"] for ls in self.config["load_site"] if ls["name"] == load_name)
        p2 = next(ds["position"] for ds in self.config["dump_site"] if ds["name"] == dump_name)
        dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) / 10.0
        return round(dist, 1)

    def _run_openmines(self, om_config: dict) -> dict:
        """Launches OpenMines simulation using the library classes directly."""
        # 1. Resolve dispatcher
        if self.dispatcher_name == "SmartDispatcher":
            # For SmartDispatcher optimization we proxy to NearestDispatcher
            from openmines.src.dispatch_algorithms.nearest_dispatcher import NearestDispatcher
            dispatcher = NearestDispatcher()
        else:
            from openmines.src.dispatch_algorithms.naive_dispatcher import NaiveDispatcher
            dispatcher = NaiveDispatcher()
            
        mine = Mine(om_config["mine"]["name"], log_path=os.path.join(os.getcwd(), "logs"))
        mine.add_dispatcher(dispatcher)
        
        # 2. Build Charging Site & Trucks
        charging_site = ChargingSite(om_config["charging_site"]["name"], position=om_config["charging_site"]["position"])
        for truck_config in om_config["charging_site"]["trucks"]:
            for _ in range(truck_config["count"]):
                truck = Truck(
                    name=f"{truck_config['type']}{_ + 1}",
                    truck_capacity=truck_config["capacity"],
                    truck_speed=truck_config["speed"]
                )
                charging_site.add_truck(truck)
                
        # 3. Build Load Sites
        for ls_c in om_config["load_sites"]:
            load_site = LoadSite(name=ls_c["name"], position=ls_c["position"])
            for sh_c in ls_c["shovels"]:
                shovel = Shovel(
                    name=sh_c["name"],
                    shovel_tons=sh_c["tons"],
                    shovel_cycle_time=sh_c["cycle_time"],
                    position_offset=sh_c["position_offset"]
                )
                load_site.add_shovel(shovel)
            load_site.add_parkinglot(position_offset=ls_c["parkinglot"]["position_offset"], name=ls_c["parkinglot"]["name"])
            mine.add_load_site(load_site)
            
        # 4. Build Dump Sites
        for ds_c in om_config["dump_sites"]:
            dump_site = DumpSite(name=ds_c["name"], position=ds_c["position"])
            for dp_c in ds_c["dumpers"]:
                for _ in range(dp_c["count"]):
                    dumper = Dumper(
                        name=f"{ds_c['name']}-点位{_}",
                        dumper_cycle_time=dp_c["cycle_time"],
                        position_offset=dp_c["position_offset"]
                    )
                    dump_site.add_dumper(dumper)
            dump_site.add_parkinglot(position_offset=ds_c["parkinglot"]["position_offset"], name=ds_c["parkinglot"]["name"])
            mine.add_dump_site(dump_site)
            
        # 5. Build Road Network
        road = Road(
            l2d_road_matrix=np.array(om_config["road"]["l2d_road_matrix"]),
            d2l_road_matrix=np.array(om_config["road"]["d2l_road_matrix"]),
            charging_to_load_road_matrix=om_config["road"]["charging_to_load_road_matrix"]
        )
        mine.add_road(road)
        mine.add_charging_site(charging_site)
        
        # 6. Synchronously run SimPy to completion
        ticks = mine.start(total_time=om_config["sim_time"])
        return ticks

    def init_db_state(self):
        conn = get_connection()
        cursor = conn.cursor()
        for om_name, t_id in self.truck_mapping.items():
            p_start = self.points["DemoChargingSite"]
            cursor.execute("""
            INSERT OR REPLACE INTO equipment_state 
            (equipment_id, equipment_type, current_route, current_position_x, current_position_y, speed, status, driver_id, risk_level, fatigue_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (t_id, "MiningTruck", "ROUTE-01", p_start[0], p_start[1], 0.0, "init", f"DRIVER-{t_id[-2:]}", "low", 0))
        conn.commit()
        conn.close()

    def step(self) -> List[dict]:
        self.current_tick += 1
        
        # Read safety blockages and driver fatigue states from DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT route_id, status FROM routes")
        routes_db = {row["route_id"]: row["status"] for row in cursor.fetchall()}
        cursor.execute("SELECT equipment_id, risk_level, fatigue_score FROM equipment_state")
        trucks_db = {row["equipment_id"]: {"risk_level": row["risk_level"], "fatigue_score": row["fatigue_score"]} for row in cursor.fetchall()}
        conn.close()
        
        # Retrieve tick packet from pre-calculated ticks
        tick_index = min(max(self.current_tick - 1, 0), 119)
        tick_data = self.ticks.get(tick_index)
        if not tick_data:
            tick_data = self.ticks.get(119)
            
        updated_trucks = []
        for om_name, om_truck in tick_data["truck_states"].items():
            truck_id = self.truck_mapping.get(om_name)
            if not truck_id:
                continue
                
            db_info = trucks_db.get(truck_id, {"risk_level": "low", "fatigue_score": 0})
            risk_level = db_info["risk_level"]
            fatigue_score = db_info["fatigue_score"]
            
            # Map OpenMines state code to project status string
            state_int = om_truck["state"]
            if state_int in [-1, 6]:
                status = "stopped" if state_int == 6 else "init"
            elif state_int in [-2, 0]:
                status = "back"
            elif state_int == 1:
                status = "idle"
            elif state_int == 2:
                status = "loading"
            elif state_int == 3:
                status = "haul"
            elif state_int == 4:
                status = "idle"
            elif state_int == 5:
                status = "unload"
            else:
                status = "idle"
                
            # If critical risk (e.g. driver asleep), stop the truck
            if risk_level == "critical":
                status = "stopped"
                speed = 0.0
                if truck_id in self.last_positions:
                    x, y = self.last_positions[truck_id]
                else:
                    x, y = om_truck["position"]
            else:
                x, y = om_truck["position"]
                if status in ["back", "haul"]:
                    speed = 25.0
                else:
                    speed = 0.0
                    
            self.last_positions[truck_id] = [x, y]
            
            # Calculate energy/fuel
            if status in ["back", "init"]:
                energy_status = "moving_empty"
                dist_moved = (speed / 60.0)
            elif status == "haul":
                energy_status = "moving_loaded"
                dist_moved = (speed / 60.0)
            elif status == "stopped":
                energy_status = "stopped"
                dist_moved = 0.0
            elif status == "loading":
                energy_status = "loading"
                dist_moved = 0.0
            elif status == "unload":
                energy_status = "unload"
                dist_moved = 0.0
            else:
                energy_status = "idle"
                dist_moved = 0.0
                
            if energy_status in ["moving_empty", "moving_loaded"]:
                fuel = self.energy_layer.calculate_fuel(energy_status, dist_moved, 0.0)
            else:
                fuel = self.energy_layer.calculate_fuel(energy_status, 0.0, 1.0/60.0)
                
            self.total_fuel += fuel
            if energy_status in ["stopped", "loading", "unload", "idle"]:
                self.idle_fuel += fuel
                self.truck_idle_time += 1.0/60.0
                
            # Proximity-based route identification
            p_s1 = self.points["Shovel-01"]
            p_s2 = self.points["Shovel-02"]
            p_s3 = self.points["Shovel-03"]
            d_s1 = math.sqrt((x-p_s1[0])**2 + (y-p_s1[1])**2)
            d_s2 = math.sqrt((x-p_s2[0])**2 + (y-p_s2[1])**2)
            d_s3 = math.sqrt((x-p_s3[0])**2 + (y-p_s3[1])**2)
            
            if d_s3 < d_s1 and d_s3 < d_s2:
                route_id = "ROUTE-03"
            elif d_s2 < d_s1 and d_s2 < d_s3:
                route_id = "ROUTE-02"
            else:
                route_id = "ROUTE-01"
                
            updated_trucks.append({
                "equipment_id": truck_id,
                "equipment_type": "MiningTruck",
                "current_route": route_id,
                "current_position_x": x,
                "current_position_y": y,
                "speed": speed,
                "status": status,
                "driver_id": f"DRIVER-{truck_id[-2:]}",
                "risk_level": risk_level,
                "fatigue_score": fatigue_score
            })
            
        # Proximity violations check
        violations = self.safety_layer.detect_dangerous_proximity(updated_trucks)
        self.safety_events += len(violations)
        
        # Accumulate production states from OpenMines tick states
        self.produced_tons = tick_data["mine_states"]["produced_tons"]
        self.completed_trips = tick_data["mine_states"]["service_count"]
        
        # Save updated states to database
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

    def save_run_kpis(self, run_id: str):
        conn = get_connection()
        cursor = conn.cursor()
        
        avg_cycle = (self.truck_idle_time * 60 + 20) / max(self.completed_trips, 1)
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
