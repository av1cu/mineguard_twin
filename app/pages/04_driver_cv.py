import streamlit as st
import cv2
import sys
import os
import numpy as np
import urllib.request
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

st.set_page_config(page_title="Driver Eye State Monitor", layout="wide")

st.title("👁️ Driver Eye State Monitor (Этап 3 - Гибридный)")
st.markdown("""
Этот модуль выполняет анализ состояния глаз водителя. 
Поддерживает калибровку, временное сглаживание по скользящему окну и классификацию состояний (**OPEN**, **PARTIALLY CLOSED**, **CLOSED**).
""")

# Setup paths and download task model if not exists
model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "cv_driver", "models"))
os.makedirs(model_dir, exist_ok=True)
model_path = os.path.join(model_dir, "face_landmarker.task")

@st.cache_resource
def get_model_file():
    if not os.path.exists(model_path):
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        try:
            with st.spinner("Загрузка модели Face Landmarker (float16)..."):
                urllib.request.urlretrieve(url, model_path)
            st.success("Модель успешно загружена!")
        except Exception as e:
            st.error(f"Не удалось загрузить файл модели: {e}")
    return model_path

model_file = get_model_file()

# MediaPipe index mapping for eyes (6-point EAR calculation)
L_EYE_INDICES = [362, 385, 387, 263, 373, 380]
R_EYE_INDICES = [33, 160, 158, 133, 153, 144]

def calculate_single_ear(landmarks, eye_indices) -> float:
    p = [np.array([landmarks[i].x, landmarks[i].y]) for i in eye_indices]
    d_v1 = np.linalg.norm(p[1] - p[5])
    d_v2 = np.linalg.norm(p[2] - p[4])
    d_h = np.linalg.norm(p[0] - p[3])
    ear = (d_v1 + d_v2) / (2.0 * d_h + 1e-6)
    return float(ear)

# Session state initialization
if "calibrated" not in st.session_state:
    st.session_state.calibrated = False
if "calibrating" not in st.session_state:
    st.session_state.calibrating = False
if "calibration_frames" not in st.session_state:
    st.session_state.calibration_frames = []
if "ear_open" not in st.session_state:
    st.session_state.ear_open = 0.28
if "ear_window" not in st.session_state:
    st.session_state.ear_window = []

WINDOW_SIZE = 8

# Option selection: Browser Camera vs Live Host Camera
mode = st.radio("Режим работы камеры:", [
    "Камера браузера (Работает в Docker на Windows)", 
    "Прямой поток веб-камеры (Только локальный запуск)"
])

# Thresholds calculation
ear_open = st.session_state.ear_open
threshold_open = ear_open * 0.80
threshold_closed = ear_open * 0.68

# Status & Live metrics placeholders
st.subheader("📊 Показатели состояния глаз:")
col_s1, col_s2, col_s3, col_s4 = st.columns(4)
metric_state = col_s1.empty()
metric_ear = col_s2.empty()
metric_avg_ear = col_s3.empty()
metric_cal_status = col_s4.empty()

# Helper to update metrics layout
def update_metrics_display(state_label, ear_l, ear_r, smoothed_ear):
    metric_state.markdown(f"### Состояние: {state_label}")
    metric_ear.metric("Текущий EAR Left / Right", f"{ear_l:.3f} / {ear_r:.3f}")
    metric_avg_ear.metric("Сглаженный EAR (Окно)", f"{smoothed_ear:.3f}")
    metric_cal_status.metric("Порог (Open / Closed)", f"{threshold_open:.3f} / {threshold_closed:.3f}")

# Reset placeholders
update_metrics_display("N/A", 0.0, 0.0, 0.0)

# Import helper
def get_face_landmarker():
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1
        )
        return vision.FaceLandmarker.create_from_options(options)
    except Exception as e:
        st.error(f"Не удалось инициализировать MediaPipe: {e}")
        return None

if mode == "Камера браузера (Работает в Docker на Windows)":
    st.info("📷 Сделайте снимок лица. Браузер захватит кадр и передаст его в контейнер на обработку.")
    
    # Calibration inside browser mode
    col_btn, col_info = st.columns(2)
    with col_btn:
        calibrate_btn = st.button("🎯 Использовать следующий снимок для калибровки открытых глаз")
        if calibrate_btn:
            st.session_state.calibrating_true_next = True
            st.info("Калибровка активирована. Сделайте снимок с широко открытыми глазами.")
            
    with col_info:
        if st.session_state.calibrated:
            st.success(f"Базовый EAR открытых глаз: `{st.session_state.ear_open:.3f}`")
        else:
            st.warning("Глаза водителя не откалиброваны. Используются стандартные пороги.")
            
    img_file = st.camera_input("Сделать снимок лица")
    
    if img_file:
        bytes_data = img_file.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb_img.shape
        
        landmarker = get_face_landmarker()
        if landmarker:
            import mediapipe as mp
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)
            result = landmarker.detect(mp_image)
            
            if result.face_landmarks:
                face_landmarks = result.face_landmarks[0]
                
                # Calculate EAR
                ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
                ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
                ear_avg = (ear_l + ear_r) / 2.0
                
                # Handle calibration
                if getattr(st.session_state, "calibrating_true_next", False):
                    st.session_state.ear_open = ear_avg
                    st.session_state.calibrated = True
                    st.session_state.calibrating_true_next = False
                    st.success("Калибровка выполнена!")
                    time.sleep(0.5)
                    st.rerun()
                
                # Push to sliding window
                st.session_state.ear_window.append(ear_avg)
                if len(st.session_state.ear_window) > WINDOW_SIZE:
                    st.session_state.ear_window.pop(0)
                    
                # Smooth EAR
                smoothed_ear = float(np.mean(st.session_state.ear_window))
                
                # Classification
                if smoothed_ear >= threshold_open:
                    state_label = ":green[**OPEN**]"
                elif smoothed_ear <= threshold_closed:
                    state_label = ":red[**CLOSED**]"
                else:
                    state_label = ":orange[**PARTIALLY CLOSED**]"
                    
                update_metrics_display(state_label, ear_l, ear_r, smoothed_ear)
                
                # Draw points on face
                for lm in face_landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(rgb_img, (cx, cy), 1, (0, 255, 0), -1)
                    
                # Draw eyes contours in red/blue
                for idx in L_EYE_INDICES + R_EYE_INDICES:
                    lm = face_landmarks[idx]
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(rgb_img, (cx, cy), 3, (0, 0, 255), -1)
                    
                st.image(rgb_img, use_container_width=True)
            else:
                st.warning("Лицо не обнаружено на снимке.")
                update_metrics_display("**Лицо не обнаружено**", 0.0, 0.0, 0.0)

else:
    # Live webcam via OpenCV
    st.info("⚠️ Прямой поток с OpenCV работает только при ручном запуске Streamlit на хост-машине (не в Docker).")
    
    # Calibration inside live mode
    col_live1, col_live2 = st.columns(2)
    with col_live1:
        if st.button("🎯 Запустить калибровку открытых глаз (30 кадров)"):
            st.session_state.calibrating = True
            st.session_state.calibration_frames = []
            st.session_state.calibrated = False
            st.info("Пожалуйста, смотрите прямо в камеру...")
            
    with col_live2:
        if st.session_state.calibrated:
            st.success(f"Базовый EAR открытых глаз: `{st.session_state.ear_open:.3f}`")
        else:
            st.warning("Глаза не откалиброваны.")
            
    run_camera = st.checkbox("🎥 Запустить прямой поток")
    frame_placeholder = st.image([])
    
    if run_camera:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Не удалось открыть камеру на сервере. В контейнерах Docker прямой доступ к веб-камере хоста заблокирован.")
            st.info("👉 Используйте режим **'Камера браузера'** выше или запустите скрипт локально: `python cv_driver/webcam_demo.py`")
        else:
            try:
                import mediapipe as mp
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision
                
                base_options = python.BaseOptions(model_asset_path=model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=1
                )
                
                with vision.FaceLandmarker.create_from_options(options) as landmarker:
                    while run_camera:
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            break
                        frame = cv2.flip(frame, 1)
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, _ = rgb_frame.shape
                        
                        # Process with Tasks API
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                        result = landmarker.detect(mp_image)
                        
                        if result.face_landmarks:
                            face_landmarks = result.face_landmarks[0]
                            
                            ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
                            ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
                            ear_avg = (ear_l + ear_r) / 2.0
                            
                            # Handle calibration
                            if st.session_state.calibrating:
                                st.session_state.calibration_frames.append(ear_avg)
                                if len(st.session_state.calibration_frames) >= 30:
                                    st.session_state.ear_open = float(np.mean(st.session_state.calibration_frames))
                                    st.session_state.calibrated = True
                                    st.session_state.calibrating = False
                                    st.rerun()
                                    
                            # Push to window
                            st.session_state.ear_window.append(ear_avg)
                            if len(st.session_state.ear_window) > WINDOW_SIZE:
                                st.session_state.ear_window.pop(0)
                                
                            smoothed_ear = float(np.mean(st.session_state.ear_window))
                            
                            if smoothed_ear >= threshold_open:
                                state_label = ":green[**OPEN**]"
                            elif smoothed_ear <= threshold_closed:
                                state_label = ":red[**CLOSED**]"
                            else:
                                state_label = ":orange[**PARTIALLY CLOSED**]"
                                
                            update_metrics_display(state_label, ear_l, ear_r, smoothed_ear)
                            
                            # Draw general landmarks
                            for lm in face_landmarks:
                                cx, cy = int(lm.x * w), int(lm.y * h)
                                cv2.circle(rgb_frame, (cx, cy), 1, (0, 255, 0), -1)
                                
                            # Highlight eye landmarks in red
                            for idx in L_EYE_INDICES + R_EYE_INDICES:
                                lm = face_landmarks[idx]
                                cx, cy = int(lm.x * w), int(lm.y * h)
                                cv2.circle(rgb_frame, (cx, cy), 3, (0, 0, 255), -1)
                        else:
                            update_metrics_display("**Лицо не обнаружено**", 0.0, 0.0, 0.0)
                            
                        frame_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
                        time.sleep(0.03)
            except Exception as e:
                st.error(f"Ошибка: {e}")
            finally:
                cap.release()
