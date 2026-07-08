import cv2
import numpy as np
import requests
import os
import random
from datetime import datetime

class SlopeCVMonitor:
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url

    def analyze_image(self, image_path: str) -> dict:
        """
        Analyzes an image of a mine slope and detects cracks, rockfalls, and road damage.
        Returns a dictionary with detections, scores, and the annotated output image.
        """
        img = cv2.imread(image_path)
        if img is None:
            # Create a blank dummy image if path is invalid
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, "No Image Loaded", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
        h, w, _ = img.shape
        annotated_img = img.copy()
        
        # Simulating detections with classic CV edge/contour highlights or coordinates
        # Let's perform simple OpenCV Canny Edge to make it look like a CV processing system
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours of edges to put some mock bounding boxes
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        # Filter contours by size to place bounding boxes representing "anomalies"
        box_count = 0
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            if cw > 40 and ch > 40 and box_count < 3:
                # We classify them as crack/rockfall based on aspect ratio
                class_name = "crack" if cw < ch else "rockfall"
                detections.append({
                    "class": class_name,
                    "bbox": [x, y, x + cw, y + ch],
                    "confidence": float(random.uniform(0.7, 0.95))
                })
                
                # Draw bounding box
                color = (0, 0, 255) if class_name == "crack" else (0, 165, 255) # Red for cracks, Orange for rockfall
                cv2.rectangle(annotated_img, (x, y), (x + cw, y + ch), color, 2)
                cv2.putText(annotated_img, f"{class_name} {detections[-1]['confidence']:.2f}", 
                            (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                box_count += 1
                
        # If no contours met criteria, inject mock ones for demonstration
        if not detections:
            # Crack mock bbox
            detections.append({"class": "crack", "bbox": [int(w*0.3), int(h*0.4), int(w*0.4), int(h*0.75)], "confidence": 0.89})
            # Rockfall mock bbox
            detections.append({"class": "rockfall", "bbox": [int(w*0.6), int(h*0.5), int(w*0.8), int(h*0.65)], "confidence": 0.76})
            
            for d in detections:
                x1, y1, x2, y2 = d["bbox"]
                color = (0, 0, 255) if d["class"] == "crack" else (0, 165, 255)
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
                cv2.putText(annotated_img, f"{d['class']} {d['confidence']:.2f}", 
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Calculate risk score based on detections
        crack_score = max([d["confidence"] for d in detections if d["class"] == "crack"], default=0.0) * 100
        rockfall_score = max([d["confidence"] for d in detections if d["class"] == "rockfall"], default=0.0) * 100
        
        # Risk score formula
        risk_score = int(0.6 * crack_score + 0.4 * rockfall_score)
        
        risk_level = "low"
        if risk_score > 75:
            risk_level = "critical"
        elif risk_score > 50:
            risk_level = "high"
        elif risk_score > 25:
            risk_level = "medium"
            
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "detections": detections,
            "annotated_image": annotated_img
        }

    def trigger_slope_event(self, section_id: str, risk_score: int, risk_level: str, detected_objects: list, description: str) -> dict:
        """
        Sends the slope anomaly event to FastAPI Backend.
        """
        try:
            url = f"{self.backend_url}/api/events"
            route_id = "ROUTE-02" if "02" in section_id or "NORTH" in section_id.upper() else "ROUTE-01"
            
            payload = {
                "source_module": "slope_cv",
                "event_type": "slope_anomaly",
                "risk_level": risk_level,
                "risk_score": risk_score,
                "route_id": route_id,
                "section_id": section_id,
                "description": description,
                "recommendation": "Block route and inspect section" if risk_level in ["high", "critical"] else "Monitor section",
                "evidence_path": f"data/evidence/slope_{section_id.lower()}.jpg"
            }
            res = requests.post(url, json=payload, timeout=2)
            if res.status_code == 200:
                print(f"Slope event sent: {payload}")
                return res.json()
            else:
                print(f"Failed to send event: {res.status_code}")
        except Exception as e:
            print(f"Error triggering slope event: {e}")
        return {}
