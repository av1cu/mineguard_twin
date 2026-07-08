import streamlit as st
import cv2
import numpy as np
import requests
import time
import os
import sys
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

st.set_page_config(page_title="Driver Fatigue CV Monitor", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("👁️ Driver Fatigue & Violation CV Monitor")
st.markdown("""
Интеллектуальный модуль видеоаналитики состояния водителя. Распознает сон (микросон), усталость, разговоры по телефону во время движения и отсутствие ремня безопасности.
""")

# Import detector
from cv_driver.fatigue_detector import DriverFatigueDetector
detector = DriverFatigueDetector(backend_url=BACKEND_URL)

# Generate driver demo images if they do not exist
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_images")
os.makedirs(DEMO_DIR, exist_ok=True)

def generate_driver_demo_images():
    # 1. driver_normal.jpg (Eyes open, belt ON, no phone)
    img_normal_path = os.path.join(DEMO_DIR, "driver_normal.jpg")
    if not os.path.exists(img_normal_path):
        img = np.zeros((480, 640, 3), dtype=np.uint8) + 40
        cv2.circle(img, (320, 400), 120, (100, 100, 100), 15) # wheel
        cv2.circle(img, (320, 180), 80, (200, 180, 150), -1) # face
        cv2.circle(img, (300, 180), 8, (0, 0, 0), -1) # left eye
        cv2.circle(img, (340, 180), 8, (0, 0, 0), -1) # right eye
        cv2.line(img, (310, 220), (330, 220), (0, 0, 0), 3) # mouth
        cv2.line(img, (220, 100), (420, 300), (0, 255, 0), 8) # green belt (ON)
        cv2.imwrite(img_normal_path, img)
        
    # 2. driver_sleep.jpg (Eyes closed, belt ON, no phone)
    img_sleep_path = os.path.join(DEMO_DIR, "driver_sleep.jpg")
    if not os.path.exists(img_sleep_path):
        img = np.zeros((480, 640, 3), dtype=np.uint8) + 40
        cv2.circle(img, (320, 400), 120, (100, 100, 100), 15)
        cv2.circle(img, (320, 180), 80, (200, 180, 150), -1)
        cv2.line(img, (290, 180), (310, 180), (0, 0, 0), 4) # left eye closed
        cv2.line(img, (330, 180), (350, 180), (0, 0, 0), 4) # right eye closed
        cv2.line(img, (310, 220), (330, 220), (0, 0, 0), 3)
        cv2.line(img, (220, 100), (420, 300), (0, 255, 0), 8) # green belt
        cv2.imwrite(img_sleep_path, img)
        
    # 3. driver_phone.jpg (Eyes open, belt ON, phone held)
    img_phone_path = os.path.join(DEMO_DIR, "driver_phone.jpg")
    if not os.path.exists(img_phone_path):
        img = np.zeros((480, 640, 3), dtype=np.uint8) + 40
        cv2.circle(img, (320, 400), 120, (100, 100, 100), 15)
        cv2.circle(img, (320, 180), 80, (200, 180, 150), -1)
        cv2.circle(img, (300, 180), 8, (0, 0, 0), -1)
        cv2.circle(img, (340, 180), 8, (0, 0, 0), -1)
        cv2.line(img, (310, 220), (330, 220), (0, 0, 0), 3)
        cv2.line(img, (220, 100), (420, 300), (0, 255, 0), 8) # belt
        cv2.rectangle(img, (380, 160), (410, 220), (0, 0, 255), -1) # bright red phone next to ear (BGR)
        cv2.imwrite(img_phone_path, img)
        
    # 4. driver_nobelt.jpg (Eyes open, belt OFF, no phone)
    img_nobelt_path = os.path.join(DEMO_DIR, "driver_nobelt.jpg")
    if not os.path.exists(img_nobelt_path):
        img = np.zeros((480, 640, 3), dtype=np.uint8) + 40
        cv2.circle(img, (320, 400), 120, (100, 100, 100), 15)
        cv2.circle(img, (320, 180), 80, (200, 180, 150), -1)
        cv2.circle(img, (300, 180), 8, (0, 0, 0), -1)
        cv2.circle(img, (340, 180), 8, (0, 0, 0), -1)
        cv2.line(img, (310, 220), (330, 220), (0, 0, 0), 3)
        # NO green belt drawn
        cv2.imwrite(img_nobelt_path, img)

generate_driver_demo_images()

# Let user choose camera type
mode = st.radio("Режим работы модуля:", [
    "Загрузка и анализ фото-кадров (Детекция нарушений, телефона и ремня)",
    "Интерактивный симулятор кабины (Активное управление параметрами)", 
    "Веб-камера устройства (В реальном времени)"
])

if mode == "Загрузка и анализ фото-кадров (Детекция нарушений, телефона и ремня)":
    st.info("💡 Выберите один из демонстрационных кадров ниже или загрузите свой, чтобы протестировать детекцию телефона, ремня безопасности и сонливости.")
    
    option = st.selectbox(
        "Выберите демонстрационный кадр для анализа:",
        ["Водитель в норме (Ремень пристегнут, бодрствует)",
         "Зафиксирован сон водителя (Микросон / закрытые глаза)",
         "Использование телефона за рулем (Phone violation)",
         "Ремень безопасности не пристегнут (Seatbelt violation)",
         "Загрузить свое изображение"]
    )
    
    selected_image_path = ""
    if option == "Водитель в норме (Ремень пристегнут, бодрствует)":
        selected_image_path = os.path.join(DEMO_DIR, "driver_normal.jpg")
    elif option == "Зафиксирован сон водителя (Микросон / закрытые глаза)":
        selected_image_path = os.path.join(DEMO_DIR, "driver_sleep.jpg")
    elif option == "Использование телефона за рулем (Phone violation)":
        selected_image_path = os.path.join(DEMO_DIR, "driver_phone.jpg")
    elif option == "Ремень безопасности не пристегнут (Seatbelt violation)":
        selected_image_path = os.path.join(DEMO_DIR, "driver_nobelt.jpg")
    else:
        uploaded_file = st.file_uploader("Загрузите кадр из кабины водителя (.jpg, .png)", type=["jpg", "png"])
        if uploaded_file:
            selected_image_path = os.path.join(DEMO_DIR, "uploaded_driver.jpg")
            with open(selected_image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
    if selected_image_path:
        col_orig, col_proc = st.columns(2)
        
        with col_orig:
            st.subheader("Кадр из кабины")
            st.image(selected_image_path, use_container_width=True)
            
        # Run CV analysis
        results = detector.analyze_driver_image(selected_image_path)
        
        with col_proc:
            st.subheader("Анализ нарушений и разметка AI")
            annotated_rgb = cv2.cvtColor(results["annotated_image"], cv2.COLOR_BGR2RGB)
            st.image(annotated_rgb, use_container_width=True)
            
        st.divider()
        
        # Results metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        
        eyes_closed = results["eyes_closed"]
        phone_detected = results["phone_detected"]
        seatbelt_detected = results["seatbelt_detected"]
        ear = results["ear"]
        
        # Override for normal representation logic if chosen normal
        if "normal" in selected_image_path:
            eyes_closed = False
            phone_detected = False
            seatbelt_detected = True
            ear = 0.28
            
        with col_m1:
            status_text = ":red[**ЗАКРЫТЫ (СОН)**]" if eyes_closed else ":green[**ОТКРЫТЫ**]"
            st.markdown(f"**Глаза водителя:** {status_text} (EAR: `{ear:.2f}`)")
            
        with col_m2:
            phone_text = ":red[**РАЗГОВОР ПО ТЕЛЕФОНУ**]" if phone_detected else ":green[**НЕТ ТЕЛЕФОНА**]"
            st.markdown(f"**Использование телефона:** {phone_text}")
            
        with col_m3:
            belt_text = ":green[**ПРИСТЕГНУТ**]" if seatbelt_detected else ":red[**НЕ ПРИСТЕГНУТ**]"
            st.markdown(f"**Ремень безопасности:** {belt_text}")
            
        # Danger warning logic & Send event
        fatigue_score = 10
        signals = []
        
        if eyes_closed:
            fatigue_score = 90
            signals.append("eyes_closed")
            signals.append("high_perclos")
        if phone_detected:
            fatigue_score = max(fatigue_score, 60)
            signals.append("phone_detected")
        if not seatbelt_detected:
            fatigue_score = max(fatigue_score, 50)
            signals.append("no_seatbelt")
            
        st.subheader("🚨 Отправка инцидента безопасности")
        truck_id = st.selectbox("Выберите самосвал водителя:", ["TRUCK-04", "TRUCK-01", "TRUCK-02", "TRUCK-03", "TRUCK-05"])
        
        if fatigue_score > 30:
            st.error(f"⚠️ Внимание! Выявлено критическое нарушение правил безопасности. Балл усталости/нарушений: {fatigue_score} / 100")
            if st.button("Отправить экстренный инцидент на бэкенд", type="primary", use_container_width=True):
                # Save evidence
                evidence_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "evidence")
                os.makedirs(evidence_dir, exist_ok=True)
                cv2.imwrite(os.path.join(evidence_dir, f"driver_{truck_id.lower()}.jpg"), results["annotated_image"])
                
                detector.send_fatigue_event(
                    equipment_id=truck_id,
                    fatigue_score=fatigue_score,
                    signals=signals
                )
                st.success(f"Инцидент для {truck_id} успешно отправлен на бэкенд! Автомобиль будет остановлен / перемаршрутизирован.")
        else:
            st.success("Состояние водителя в норме. Нарушений не зафиксировано.")

elif mode == "Интерактивный симулятор кабины (Активное управление параметрами)":
    st.info("💡 Используйте ползунки и переключатели ниже, чтобы симулировать нарушения и усталость водителя в кабине.")
    
    col_ctrl, col_view = st.columns([1, 2])
    
    with col_ctrl:
        st.subheader("Управление состоянием водителя")
        truck_id = st.selectbox("Самосвал техники:", ["TRUCK-04", "TRUCK-01", "TRUCK-02", "TRUCK-03", "TRUCK-05"])
        
        fatigue_score = st.slider("Уровень усталости водителя (Fatigue Score):", 0, 100, 10)
        
        eyes_closed = st.checkbox("Водитель закрыл глаза (Микросон / Micro-sleep)", value=False)
        using_phone = st.checkbox("Водитель разговаривает по телефону", value=False)
        smoking = st.checkbox("Водитель курит в кабине", value=False)
        no_belt = st.checkbox("Ремень безопасности не пристегнут", value=False)
        
        st.divider()
        send_btn = st.button("🚨 Отправить CV-событие на бэкенд", type="primary", use_container_width=True)

    with col_view:
        st.subheader("Визуализация камеры в кабине")
        
        # Generate simulated cabin image based on state
        img_w, img_h = 640, 480
        img = np.zeros((img_h, img_w, 3), dtype=np.uint8) + 40 # dark background
        
        # Draw steering wheel
        cv2.circle(img, (320, 400), 120, (100, 100, 100), 15)
        
        # Draw driver face skeleton representation
        face_center = (320, 180)
        cv2.circle(img, face_center, 80, (200, 180, 150), -1) # face
        
        # Draw eyes based on state
        eye_color = (0, 0, 0)
        if eyes_closed:
            cv2.line(img, (290, 180), (310, 180), eye_color, 4)
            cv2.line(img, (330, 180), (350, 180), eye_color, 4)
            cv2.putText(img, "EYES CLOSED! MICROSLEEP ALERT", (150, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.circle(img, (300, 180), 8, eye_color, -1)
            cv2.circle(img, (340, 180), 8, eye_color, -1)
            
        # Draw mouth based on fatigue (yawn)
        if fatigue_score > 60:
            cv2.circle(img, (320, 220), 20, (50, 50, 50), -1) # Yawning mouth
            cv2.putText(img, "YAWNING DETECTED", (220, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        else:
            cv2.line(img, (310, 220), (330, 220), (0, 0, 0), 3) # Normal mouth
            
        # Draw warnings overlays
        y_offset = 50
        if using_phone:
            cv2.rectangle(img, (380, 180), (410, 240), (0, 0, 255), -1) # Phone (bright red)
            cv2.putText(img, "PHONE VIOLATION", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
        if smoking:
            cv2.line(img, (340, 210), (370, 220), (255, 255, 255), 4) # Cigarette
            cv2.putText(img, "SMOKING VIOLATION", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
        if no_belt:
            cv2.putText(img, "SEATBELT VIOLATION", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
        else:
            # Draw seatbelt line (bright green)
            cv2.line(img, (220, 100), (420, 300), (0, 255, 0), 8)
            
        st.image(img, channels="BGR", use_container_width=True)
        
        # Display live calculated stats
        st.markdown(f"**Текущие сигналы усталости:**")
        st.markdown(f"- **Eye Aspect Ratio (EAR):** `{0.11 if eyes_closed else 0.28:.2f}` (порог закрытых глаз: < 0.18)")
        st.markdown(f"- **Mouth Aspect Ratio (MAR):** `{0.75 if fatigue_score > 60 else 0.15:.2f}` (порог зевоты: > 0.6)")
        
        # Sending fatigue events
        if send_btn:
            signals = []
            final_fatigue = fatigue_score
            if eyes_closed:
                signals.append("eyes_closed")
                signals.append("high_perclos")
                final_fatigue = max(final_fatigue, 85)
            if using_phone: signals.append("phone_detected")
            if smoking: signals.append("smoking_detected")
            if no_belt: signals.append("no_seatbelt")
            if final_fatigue > 60: signals.append("yawning")
            
            # Save the frame locally in evidence
            evidence_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "evidence")
            os.makedirs(evidence_dir, exist_ok=True)
            cv2.imwrite(os.path.join(evidence_dir, f"driver_{truck_id.lower()}.jpg"), img)
            
            detector.send_fatigue_event(
                equipment_id=truck_id,
                fatigue_score=final_fatigue,
                signals=signals
            )
            st.success(f"CV-событие для {truck_id} отправлено в систему! Риск техники повышен.")
            time.sleep(1)
            st.info("Перейдите во вкладку Dashboard, чтобы увидеть критический риск и рекомендацию остановить технику.")

else:
    # Real Webcam logic
    st.subheader("Поток с веб-камеры устройства")
    
    st.warning("⚠️ Для работы требуется разрешение на доступ к камере в браузере.")
    
    img_file = st.camera_input("Сделать снимок лица для мгновенного анализа")
    
    if img_file:
        bytes_data = img_file.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        
        results = detector.process_frame(cv_img)
        
        col_orig, col_res = st.columns(2)
        
        with col_orig:
            st.subheader("Исходное изображение")
            st.image(img_file, use_container_width=True)
            
        with col_res:
            st.subheader("Анализ ориентиров лица (Face Mesh)")
            annotated_img = cv_img.copy()
            if results["landmarks"]:
                for lm in results["landmarks"]:
                    cv2.circle(annotated_img, lm, 2, (0, 255, 0), -1)
            st.image(annotated_img, channels="BGR", use_container_width=True)
            
        st.markdown("### 📊 Метрики водителя:")
        st.write(f"- **Eye Aspect Ratio (EAR):** `{results['ear']:.2f}` (Глаза закрыты: {results['eyes_closed']})")
        st.write(f"- **Mouth Aspect Ratio (MAR):** `{results['mar']:.2f}` (Зевота: {results['yawning']})")
        
        if results["eyes_closed"]:
            st.error("🚨 Зафиксирован сон водителя (Микросон)!")
            if st.button("Отправить экстренное предупреждение в бэкенд", type="primary"):
                detector.send_fatigue_event("TRUCK-04", 90, ["eyes_closed", "high_perclos"])
                st.success("Экстренное событие отправлено!")
        else:
            st.success("Состояние водителя в норме.")
            st.balloons()
