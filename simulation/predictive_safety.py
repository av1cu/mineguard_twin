import math
from typing import List, Dict, Any

class PredictiveSafety:
    def __init__(self, safe_threshold: float = 8.0):
        self.safe_threshold = safe_threshold
        # Site points coordinates for routing vector estimation
        self.points = {
            "Shovel-01": [10.0, 20.0],
            "Shovel-02": [-15.0, 30.0],
            "Shovel-03": [5.0, -25.0],
            "Dump-01": [40.0, 0.0],
            "Dump-02": [-40.0, -10.0]
        }
        
    def analyze_telemetry(self, trucks: List[Dict[str, Any]], lookahead_seconds: float = 5.0) -> List[Dict[str, Any]]:
        warnings = []
        num_trucks = len(trucks)
        
        # 1. Estimate predicted positions for all trucks
        predicted_positions = {}
        for t in trucks:
            t_id = t["equipment_id"]
            x = t["current_position_x"]
            y = t["current_position_y"]
            speed = t.get("speed", 0.0)
            status = t.get("status", "idle")
            route_id = t.get("current_route", "ROUTE-01")
            
            # Identify target coordinates based on route and travel direction (status)
            target = [0.0, 0.0]
            if status == "haul":
                # Moving loaded from Shovel to Dump
                if route_id in ["ROUTE-01", "ROUTE-02"]:
                    target = self.points["Dump-01"]
                else:
                    target = self.points["Dump-02"]
            elif status == "back":
                # Moving empty from Dump to Shovel
                if route_id == "ROUTE-01":
                    target = self.points["Shovel-01"]
                elif route_id == "ROUTE-02":
                    target = self.points["Shovel-02"]
                elif route_id == "ROUTE-03":
                    target = self.points["Shovel-03"]
                else:
                    target = self.points["Shovel-01"]
            else:
                target = [x, y]
                
            dx = target[0] - x
            dy = target[1] - y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist > 0.001 and speed > 0.0:
                ux = dx / dist
                uy = dy / dist
                # speed is in km/h, convert to coordinate units/s (assuming 1 unit = 1 km)
                ds = lookahead_seconds * (speed / 3600.0)
                pred_x = x + ux * ds
                pred_y = y + uy * ds
            else:
                pred_x = x
                pred_y = y
                
            predicted_positions[t_id] = (pred_x, pred_y)
            
        # 2. Check all pairs for predictive collision risks
        for i in range(num_trucks):
            for j in range(i + 1, num_trucks):
                t1 = trucks[i]
                t2 = trucks[j]
                
                t1_id = t1["equipment_id"]
                t2_id = t2["equipment_id"]
                
                pos1 = predicted_positions[t1_id]
                pos2 = predicted_positions[t2_id]
                
                # Calculate predicted distance
                pred_dist = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                
                if pred_dist < self.safe_threshold:
                    # Calculate formula parameters
                    # Proximity component: 0 if at threshold, 1 if touch
                    proximity_val = max(0.0, 1.0 - (pred_dist / self.safe_threshold))
                    
                    # Fatigue component: average driver fatigue normalized 0-1
                    fatigue_val = (t1.get("fatigue_score", 0) + t2.get("fatigue_score", 0)) / 2.0 / 100.0
                    
                    # Relative speed component: difference in speeds normalized by 50 km/h max
                    rel_speed = abs(t1.get("speed", 0.0) - t2.get("speed", 0.0))
                    speed_val = min(1.0, rel_speed / 50.0)
                    
                    # Compute combined risk score
                    risk_score = 0.5 * proximity_val + 0.3 * fatigue_val + 0.2 * speed_val
                    
                    warnings.append({
                        "equipment1": t1_id,
                        "equipment2": t2_id,
                        "risk_score": round(risk_score * 100.0, 1), # as percentage
                        "predicted_time": "через 5 секунд",
                        "recommendation": f"Снизить скорость {t1_id} или {t2_id} для увеличения безопасной дистанции"
                    })
                    
        return warnings
