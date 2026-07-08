import streamlit as st
import cv2
import sys
import os
import numpy as np
import urllib.request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

st.set_page_config(page_title="Driver Face Landmark Detection & EAR", layout="wide")

st.title("👁️ Driver Eye Aspect Ratio (EAR) Monitor (Этап 2)")
st.markdown("""
Этот модуль рассчитывает показатель **Eye Aspect Ratio (EAR)** отдельно для левого и правого глаза, а также вычисляет средний EAR в режиме реального времени.
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

# Trigger download
model_file = get_model_file()

# MediaPipe index mapping for eyes (6-point EAR calculation)
L_EYE_INDICES = [362, 385, 387, 263, 373, 380]
R_EYE_INDICES = [33, 160, 158, 133, 153, 144]

def calculate_single_ear(landmarks, eye_indices) -> float:
    """
    Eye Aspect Ratio calculation.
    Formula: EAR = (|p1 - p5| + |p2 - p4|) / (2 * |p0 - p3|)
    """
    p = [np.array([landmarks[i].x, landmarks[i].y]) for i in eye_indices]
    
    # Vertical distances
    d_v1 = np.linalg.norm(p[1] - p[5])
    d_v2 = np.linalg.norm(p[2] - p[4])
    
    # Horizontal distance
    d_h = np.linalg.norm(p[0] - p[3])
    
    ear = (d_v1 + d_v2) / (2.0 * d_h + 1e-6)
    return float(ear)

# Option selection: Browser Camera vs Live Host Camera
mode = st.radio("Режим камеры:", [
    "Камера браузера (Рекомендуется для Docker)", 
    "Прямой поток веб-камеры (Только при локальном запуске вне Docker)"
])

# Create metrics display grid
st.subheader("📈 Показатели EAR в реальном времени:")
col_l, col_r, col_avg = st.columns(3)
val_l = col_l.empty()
val_r = col_r.empty()
val_avg = col_avg.empty()

# Initialize empty values
val_l.metric("EAR Left", "0.000")
val_r.metric("EAR Right", "0.000")
val_avg.metric("Средний EAR", "0.000")

def process_with_tasks_api(rgb_img):
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        # Configure Landmarker Options
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1
        )
        
        with vision.FaceLandmarker.create_from_options(options) as landmarker:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)
            result = landmarker.detect(mp_image)
            
            annotated_img = rgb_img.copy()
            h, w, _ = annotated_img.shape
            
            if result.face_landmarks:
                face_landmarks = result.face_landmarks[0]
                
                # Calculate EAR
                ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
                ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
                ear_avg = (ear_l + ear_r) / 2.0
                
                # Update metrics
                val_l.metric("EAR Left", f"{ear_l:.3f}")
                val_r.metric("EAR Right", f"{ear_r:.3f}")
                val_avg.metric("Средний EAR", f"{ear_avg:.3f}")
                
                # Draw landmarks
                for lm in face_landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(annotated_img, (cx, cy), 1, (0, 255, 0), -1)
                    
                # Highlight eye landmarks in red
                for idx in L_EYE_INDICES + R_EYE_INDICES:
                    lm = face_landmarks[idx]
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(annotated_img, (cx, cy), 3, (255, 0, 0), -1)
                    
                return True, annotated_img
            else:
                return False, annotated_img
                
    except Exception as e:
        st.error(f"Ошибка загрузки MediaPipe Tasks API: {e}")
        return False, rgb_img

if mode == "Камера браузера (Рекомендуется для Docker)":
    st.info("📷 Сделайте снимок в панели ниже для расчета EAR.")
    img_file = st.camera_input("Сделать снимок лица")
    
    if img_file:
        bytes_data = img_file.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        
        success, annotated_img = process_with_tasks_api(rgb_img)
        if success:
            st.success("Обработка завершена!")
            st.image(annotated_img, use_container_width=True)
        else:
            st.warning("Лицо не найдено на снимке.")

else:
    # Live webcam via OpenCV
    st.info("⚠️ Прямой поток с OpenCV работает только при ручном запуске Streamlit на хост-машине (не в Docker).")
    run_camera = st.checkbox("🎥 Запустить прямой поток")
    frame_placeholder = st.image([])
    
    if run_camera:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Не удалось открыть камеру на сервере. В контейнерах Docker прямой доступ к веб-камере хоста заблокирован.")
            st.info("👉 Используйте режим **'Камера браузера (Рекомендуется для Docker)'** выше или запустите скрипт локально на компьютере: `python cv_driver/webcam_demo.py`")
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
                    import time
                    while run_camera:
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            break
                        frame = cv2.flip(frame, 1)
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Process with Tasks API
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                        result = landmarker.detect(mp_image)
                        
                        h, w, _ = rgb_frame.shape
                        if result.face_landmarks:
                            face_landmarks = result.face_landmarks[0]
                            
                            # Calculate EAR
                            ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
                            ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
                            ear_avg = (ear_l + ear_r) / 2.0
                            
                            # Update metrics
                            val_l.metric("EAR Left", f"{ear_l:.3f}")
                            val_r.metric("EAR Right", f"{ear_r:.3f}")
                            val_avg.metric("Средний EAR", f"{ear_avg:.3f}")
                            
                            # Draw general landmarks
                            for lm in face_landmarks:
                                cx, cy = int(lm.x * w), int(lm.y * h)
                                cv2.circle(rgb_frame, (cx, cy), 1, (0, 255, 0), -1)
                                
                            # Highlight eye landmarks in red
                            for idx in L_EYE_INDICES + R_EYE_INDICES:
                                lm = face_landmarks[idx]
                                cx, cy = int(lm.x * w), int(lm.y * h)
                                cv2.circle(rgb_frame, (cx, cy), 3, (255, 0, 0), -1)
                                
                        frame_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
                        time.sleep(0.03)
            except Exception as e:
                st.error(f"Ошибка: {e}")
            finally:
                cap.release()
