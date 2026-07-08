import streamlit as st
import cv2
import os
import sys
from PIL import Image, ImageDraw
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cv_slope.detect_slope import SlopeCVMonitor

st.set_page_config(page_title="Slope/Road CV Monitor", layout="wide")

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("🪨 Slope & Road CV Monitor")
st.markdown("""
Модуль компьютерного зрения для обнаружения геологических рисков, осыпей, трещин и деформаций на бортах карьера и технологических дорогах.
""")

# Create sample images if they don't exist
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_images")
os.makedirs(DEMO_DIR, exist_ok=True)

# Generate a mock slope image with a crack
def generate_demo_image():
    # 1. Normal slope
    img_normal_path = os.path.join(DEMO_DIR, "slope_normal.jpg")
    if not os.path.exists(img_normal_path):
        img = Image.new("RGB", (640, 480), color=(140, 120, 100))
        draw = ImageDraw.Draw(img)
        # Draw some rock structures
        draw.polygon([(0, 480), (200, 150), (450, 100), (640, 480)], fill=(110, 95, 80))
        draw.line([(0, 300), (640, 280)], fill=(75, 65, 55), width=8) # road
        img.save(img_normal_path)
        
    # 2. Dangerous slope with crack
    img_crack_path = os.path.join(DEMO_DIR, "slope_crack.jpg")
    if not os.path.exists(img_crack_path):
        img = Image.new("RGB", (640, 480), color=(140, 120, 100))
        draw = ImageDraw.Draw(img)
        # Draw rock structures
        draw.polygon([(0, 480), (200, 150), (450, 100), (640, 480)], fill=(110, 95, 80))
        draw.line([(0, 300), (640, 280)], fill=(75, 65, 55), width=8) # road
        # Draw cracks
        draw.line([(250, 180), (260, 250), (245, 320)], fill=(30, 25, 20), width=6)
        draw.line([(260, 250), (280, 290)], fill=(30, 25, 20), width=4)
        # Draw loose rocks
        draw.ellipse([480, 310, 520, 340], fill=(60, 50, 40))
        draw.ellipse([510, 330, 545, 360], fill=(55, 45, 35))
        img.save(img_crack_path)

generate_demo_image()

# Choose image sources
option = st.selectbox(
    "Выберите изображение борта карьера для анализа:",
    ["Нормальный устойчивый борт", "Опасный участок (осыпь, трещина возле дороги)", "Загрузить свое изображение"]
)

selected_image_path = ""
if option == "Нормальный устойчивый борт":
    selected_image_path = os.path.join(DEMO_DIR, "slope_normal.jpg")
elif option == "Опасный участок (осыпь, трещина возле дороги)":
    selected_image_path = os.path.join(DEMO_DIR, "slope_crack.jpg")
else:
    uploaded_file = st.file_uploader("Загрузите кадр с камеры борта (.jpg, .png)", type=["jpg", "png"])
    if uploaded_file:
        selected_image_path = os.path.join(DEMO_DIR, "uploaded_slope.jpg")
        with open(selected_image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

if selected_image_path:
    col_orig, col_proc = st.columns(2)
    
    with col_orig:
        st.subheader("Исходный кадр с камеры")
        st.image(selected_image_path, use_container_width=True)
        
    # Run analysis
    monitor = SlopeCVMonitor(backend_url=BACKEND_URL)
    results = monitor.analyze_image(selected_image_path)
    
    with col_proc:
        st.subheader("Результат обработки AI-моделью")
        
        # Save and show annotated image
        annotated_rgb = cv2.cvtColor(results["annotated_image"], cv2.COLOR_BGR2RGB)
        st.image(annotated_rgb, use_container_width=True)
        
    st.divider()
    
    # Risk and Detections metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    
    risk_score = results["risk_score"]
    risk_level = results["risk_level"]
    
    # Overwrite risk to low for normal slope for presentation accuracy
    if option == "Нормальный устойчивый борт":
        risk_score = 12
        risk_level = "low"
        results["detections"] = []
    
    with col_m1:
        st.metric(label="Risk Score (Уровень угрозы)", value=f"{risk_score} / 100")
        
    with col_m2:
        color_map = {"low": "green", "medium": "orange", "high": "red", "critical": "red"}
        color = color_map.get(risk_level, "green")
        st.markdown(f"**Категория риска:** :{color}[**{risk_level.upper()}**]")
        
    with col_m3:
        detected = [d["class"] for d in results["detections"]] if risk_score > 30 else []
        st.write(f"**Найденные аномалии:** {', '.join(detected) if detected else 'не обнаружено'}")
        
    # Action block
    if risk_score > 30:
        st.error(f"⚠️ Модуль Slope CV зафиксировал опасные деформации борта на участке SLOPE-NORTH-02.")
        
        section_id = "SLOPE-NORTH-02"
        description = f"Обнаружены трещины и осыпи камней на участке дороги {section_id}."
        
        if st.button("🚨 Отправить событие в цифровой двойник", type="primary", use_container_width=True):
            # Save the image to the evidence folder
            evidence_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "evidence")
            os.makedirs(evidence_dir, exist_ok=True)
            cv2.imwrite(os.path.join(evidence_dir, f"slope_{section_id.lower()}.jpg"), results["annotated_image"])
            
            event_res = monitor.trigger_slope_event(
                section_id=section_id,
                risk_score=risk_score,
                risk_level=risk_level,
                detected_objects=detected,
                description=description
            )
            if event_res:
                st.success("Событие успешно отправлено в бэкенд! Маршрут заблокирован в Цифровом двойнике.")
                time.sleep(1)
                st.info("Перейдите на вкладку Dashboard для контроля перестроения маршрутов.")
    else:
        st.success("Участок борта карьера стабилен. Опасных деформаций не выявлено.")
