import math
from typing import List, Dict, Tuple, Any

class SafetyLayer:
    def __init__(self, proximity_threshold: float = 2.0):
        # Coordinates unit proximity threshold
        self.proximity_threshold = proximity_threshold

    def detect_dangerous_proximity(self, trucks: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
        """
        Detects trucks that are too close to each other.
        Returns a list of tuples: (truck_id_1, truck_id_2, distance)
        """
        violations = []
        n = len(trucks)
        for i in range(n):
            for j in range(i + 1, n):
                t1 = trucks[i]
                t2 = trucks[j]
                
                # Only check moving or active trucks
                if t1["status"] == "stopped" or t2["status"] == "stopped":
                    continue
                    
                x1, y1 = t1.get("current_position_x"), t1.get("current_position_y")
                x2, y2 = t2.get("current_position_x"), t2.get("current_position_y")
                
                if x1 is None or y1 is None or x2 is None or y2 is None:
                    continue
                    
                dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                if dist < self.proximity_threshold:
                    violations.append((t1["equipment_id"], t2["equipment_id"], dist))
        return violations

    def calculate_truck_risk(self, fatigue_score: int, route_risk_level: str) -> str:
        """
        Calculates aggregate truck risk level based on driver fatigue score and route risk.
        """
        # If driver is asleep/critical fatigue, truck is immediately at critical risk
        if fatigue_score >= 80:
            return "critical"
            
        # If high fatigue or route is blocked/critical
        if fatigue_score >= 50 or route_risk_level in ["high", "critical"]:
            # If both are present, risk is critical
            if fatigue_score >= 50 and route_risk_level in ["high", "critical"]:
                return "critical"
            return "high"
            
        if fatigue_score >= 25 or route_risk_level == "medium":
            return "medium"
            
        return "low"
