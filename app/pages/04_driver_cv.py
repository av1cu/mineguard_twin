import streamlit as st
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

st.set_page_config(page_title="Driver Eye State Monitor", layout="wide")

st.title("👁️ Driver Eye State Monitor (Живой видеоанализ)")
st.markdown("""
Этот модуль выполняет **потоковый видеоанализ состояния глаз водителя** в реальном времени.
Используется новый MediaPipe Tasks Face Landmarker для расчета EAR и показателя PERCLOS.
""")

# Sidebar config
with st.sidebar:
    st.header("🚚 Параметры транспорта")
    truck_id = st.selectbox("Контролируемый самосвал:", ["TRUCK-04", "TRUCK-01", "TRUCK-02", "TRUCK-03", "TRUCK-05"])
    st.divider()
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    # Resolve backend URL for browser fetch (always use localhost if accessed from same machine browser)
    browser_api_url = "http://localhost:8000"
    st.write(f"Бэкенд контейнера: `{BACKEND_URL}`")
    st.write(f"Адрес API в браузере: `{browser_api_url}`")

# Mode selection
mode = st.radio("Выберите режим работы камеры:", [
    "📹 Живой видеопоток браузера (Рекомендуется для Docker/Windows)",
    "⚙️ Прямой видеопоток OpenCV (Только при запуске на Windows вне Docker)"
])

if mode == "📹 Живой видеопоток браузера (Рекомендуется для Docker/Windows)":
    st.info("💡 Этот режим захватывает видеопоток веб-камеры прямо через ваш браузер, обрабатывает кадры на сервере через API и выводит результат с частотой 10 кадров в секунду. Это обходит любые ограничения Docker на работу с веб-камерой на Windows!")
    
    # Render Embedded HTML/JS capturing webcam and sending frames to FastAPI
    html_code = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; color: #fff; background: transparent; padding: 0;">
      <div style="display: flex; gap: 20px; flex-wrap: nowrap; justify-content: center; align-items: flex-start; height: 510px;">
        <div style="position: relative; width: 680px; height: 510px; background: #0c0d12; border-radius: 12px; overflow: hidden; border: 1px solid #2d3139; box-shadow: 0 8px 30px rgba(0,0,0,0.5); flex-shrink: 0;">
          <video id="webcam" width="640" height="480" autoplay playsinline style="display:none;"></video>
          <canvas id="captureCanvas" width="640" height="480" style="display:none;"></canvas>
          <img id="outputImage" style="width: 100%; height: 100%; object-fit: cover; background: #000; display: block;" />
          <div id="loading" style="position: absolute; top: 45%; left: 0; width: 100%; text-align: center; color: #aaa; font-size: 16px;">
            🔌 Инициализация веб-камеры...
          </div>
        </div>
        
        <div style="width: 280px; height: 510px; background: #15171e; padding: 20px; border-radius: 12px; border: 1px solid #2d3139; box-shadow: 0 8px 30px rgba(0,0,0,0.3); box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; overflow-y: auto;">
          <h3 style="margin-top: 0; color: #4CAF50; border-bottom: 1px solid #333; padding-bottom: 8px;">⚙️ Калибровка</h3>
          <div style="margin-bottom: 20px;">
            <button id="btnCalibrate" style="padding: 12px 15px; font-size: 14px; font-weight: bold; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; width: 100%; transition: 0.2s;">
              🎯 Откалибровать открытые глаза
            </button>
            <p style="font-size: 12px; color: #aaa; margin-top: 8px;">Смотрите прямо в камеру с открытыми глазами при клике.</p>
          </div>
          
          <h3 style="color: #FF9800; border-bottom: 1px solid #333; padding-bottom: 8px;">📊 Состояние водителя</h3>
          
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: #ccc;">Глаза:</span>
            <span id="txtState" style="padding: 4px 8px; border-radius: 4px; background: #444; font-weight: bold; font-size: 14px; text-transform: uppercase;">N/A</span>
          </div>
          
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: #ccc;">Рот (Зевота):</span>
            <span id="txtYawn" style="padding: 4px 8px; border-radius: 4px; background: #444; font-weight: bold; font-size: 14px; text-transform: uppercase;">N/A</span>
          </div>
          
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: #ccc;">Сглаженный EAR:</span>
            <span id="txtEar" style="font-family: monospace; font-weight: bold; font-size: 16px;">0.000</span>
          </div>
          
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: #ccc;">Открытие рта (MAR):</span>
            <span id="txtMar" style="font-family: monospace; font-weight: bold; font-size: 16px;">0.000</span>
          </div>
          
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: #ccc;">Усталость (PERCLOS):</span>
            <span id="txtPerclos" style="font-family: monospace; font-weight: bold; font-size: 16px; color: #FF9800;">0.0%</span>
          </div>
          
          <div id="alertBox" style="margin-top: 25px; padding: 12px; border-radius: 4px; display: none; text-align: center; font-weight: bold; font-size: 15px; animation: blinker 1.5s linear infinite;">
            🚨 ВОДИТЕЛЬ ЗАСЫПАЕТ!
          </div>
        </div>
      </div>
    </div>

    <style>
      @keyframes blinker {
        50% { opacity: 0.5; }
      }
    </style>

    <script>
      const video = document.getElementById('webcam');
      const canvas = document.getElementById('captureCanvas');
      const context = canvas.getContext('2d');
      const outputImg = document.getElementById('outputImage');
      const loading = document.getElementById('loading');
      const txtState = document.getElementById('txtState');
      const txtYawn = document.getElementById('txtYawn');
      const txtEar = document.getElementById('txtEar');
      const txtMar = document.getElementById('txtMar');
      const txtPerclos = document.getElementById('txtPerclos');
      const btnCalibrate = document.getElementById('btnCalibrate');
      const alertBox = document.getElementById('alertBox');
      
      let calibrateNext = false;
      
      btnCalibrate.onclick = () => {
          calibrateNext = true;
          btnCalibrate.innerText = '⏳ Калибровка...';
          btnCalibrate.style.background = '#FF9800';
      };
      
      // Request webcam access
      navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(stream => {
            video.srcObject = stream;
            loading.style.display = 'none';
            
            // Start streaming frames to backend
            setInterval(sendFrame, 100); // 10 FPS (100ms)
        })
        .catch(err => {
            loading.innerHTML = '❌ Ошибка доступа к камере: <br>' + err.message + '<br><br>Пожалуйста, убедитесь, что камера подключена и вы дали разрешение в браузере.';
            console.error(err);
        });
        
      function sendFrame() {
          if (video.readyState === video.HAVE_ENOUGH_DATA) {
              // Draw video frame to canvas
              context.drawImage(video, 0, 0, canvas.width, canvas.height);
              
              // Get base64 image data
              const dataUrl = canvas.toDataURL('image/jpeg', 0.5); // Compression 0.5 for fast transport
              
              // Send to FastAPI backend
              fetch('{browser_api_url}/api/driver/stream_frame', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                      image: dataUrl,
                      equipment_id: '{truck_id}',
                      calibrate: calibrateNext
                  })
              })
              .then(res => res.json())
              .then(data => {
                  if (data.success) {
                      // Render returned annotated image with landmarks
                      outputImg.src = data.image;
                      
                      // Update text labels
                      txtState.innerText = data.state;
                      if (data.state === 'OPEN') {
                          txtState.style.background = '#4CAF50';
                          txtState.style.color = 'white';
                      } else if (data.state === 'CLOSED') {
                          txtState.style.background = '#f44336';
                          txtState.style.color = 'white';
                      } else {
                          txtState.style.background = '#ff9800';
                          txtState.style.color = 'white';
                      }
                      
                      if (data.is_yawning) {
                          txtYawn.innerText = 'ЗЕВОТА';
                          txtYawn.style.background = '#f44336';
                          txtYawn.style.color = 'white';
                      } else {
                          txtYawn.innerText = 'НОРМА';
                          txtYawn.style.background = '#4CAF50';
                          txtYawn.style.color = 'white';
                      }
                      
                      txtEar.innerText = data.smoothed_ear.toFixed(3);
                      txtMar.innerText = (data.mar || 0).toFixed(3);
                      txtPerclos.innerText = data.perclos.toFixed(1) + '%';
                      
                      // Handle alert box
                      if (data.perclos >= 25.0) {
                          alertBox.style.display = 'block';
                          alertBox.style.background = '#f44336';
                          alertBox.style.color = 'white';
                      } else {
                          alertBox.style.display = 'none';
                      }
                      
                      // Reset calibration state
                      if (calibrateNext) {
                          calibrateNext = false;
                          btnCalibrate.innerText = '🎯 Откалибровать глаза';
                          btnCalibrate.style.background = '#2196F3';
                      }
                  }
              })
              .catch(err => {
                  console.error('API Connection Error:', err);
              });
          }
      }
    </script>
    """
    
    html_code = html_code.replace("{browser_api_url}", browser_api_url).replace("{truck_id}", truck_id)
    st.components.v1.html(html_code, height=540)

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
        import cv2
        import numpy as np
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        # EAR mapping indices
        L_EYE_INDICES = [362, 385, 387, 263, 373, 380]
        R_EYE_INDICES = [33, 160, 158, 133, 153, 144]
        
        def calculate_single_ear(landmarks, eye_indices) -> float:
            p = [np.array([landmarks[idx].x, landmarks[idx].y]) for idx in eye_indices]
            d_v1 = np.linalg.norm(p[1] - p[5])
            d_v2 = np.linalg.norm(p[2] - p[4])
            d_h = np.linalg.norm(p[0] - p[3])
            return float((d_v1 + d_v2) / (2.0 * d_h + 1e-6))
            
        model_path = os.path.join(model_dir, "face_landmarker.task")
        
        # Load placeholders
        col_s1, col_s2, col_s3 = st.columns(3)
        m_state = col_s1.empty()
        m_ear = col_s2.empty()
        m_perclos = col_s3.empty()
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Не удалось открыть камеру на сервере.")
        else:
            try:
                base_options = python.BaseOptions(model_asset_path=model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=1
                )
                
                # Thresholds calculation
                ear_open = st.session_state.ear_open
                threshold_open = ear_open * 0.82
                threshold_closed = ear_open * 0.74
                
                with vision.FaceLandmarker.create_from_options(options) as landmarker:
                    while run_camera:
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            break
                        frame = cv2.flip(frame, 1)
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, _ = rgb_frame.shape
                        
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                        result = landmarker.detect(mp_image)
                        
                        if result.face_landmarks:
                            face_landmarks = result.face_landmarks[0]
                            ear_l = calculate_single_ear(face_landmarks, L_EYE_INDICES)
                            ear_r = calculate_single_ear(face_landmarks, R_EYE_INDICES)
                            ear_avg = (ear_l + ear_r) / 2.0
                            
                            # Calibration
                            if st.session_state.calibrating:
                                st.session_state.calibration_frames.append(ear_avg)
                                if len(st.session_state.calibration_frames) >= 30:
                                    st.session_state.ear_open = float(np.mean(st.session_state.calibration_frames))
                                    st.session_state.calibrated = True
                                    st.session_state.calibrating = False
                                    st.rerun()
                                    
                            # Sliding window
                            st.session_state.ear_window.append(ear_avg)
                            if len(st.session_state.ear_window) > 8:
                                st.session_state.ear_window.pop(0)
                            smoothed_ear = float(np.mean(st.session_state.ear_window))
                            
                            is_closed = False
                            if smoothed_ear >= threshold_open:
                                state_label = "OPEN"
                            elif smoothed_ear <= threshold_closed:
                                state_label = "CLOSED"
                                is_closed = True
                            else:
                                state_label = "PARTIALLY CLOSED"
                                
                            st.session_state.perclos_window.append(1 if is_closed else 0)
                            if len(st.session_state.perclos_window) > 80:
                                st.session_state.perclos_window.pop(0)
                            perclos = (sum(st.session_state.perclos_window) / len(st.session_state.perclos_window)) * 100.0
                            
                            m_state.metric("Состояние", state_label)
                            m_ear.metric("EAR", f"{smoothed_ear:.3f}")
                            m_perclos.metric("PERCLOS", f"{perclos:.1f}%")
                            
                            # Trigger event
                            if perclos >= 25.0:
                                if not st.session_state.fatigue_event_triggered:
                                    # Send POST request to backend
                                    try:
                                        requests.post(f"{BACKEND_URL}/api/driver/analyze", json={
                                            "equipment_id": truck_id,
                                            "fatigue_score": int(perclos),
                                            "detected_signals": ["high_perclos", "eyes_closed"]
                                        }, timeout=1)
                                        st.session_state.fatigue_event_triggered = True
                                    except:
                                        pass
                            elif perclos < 10.0:
                                st.session_state.fatigue_event_triggered = False
                                
                            # Draw
                            for lm in face_landmarks:
                                cx, cy = int(lm.x * w), int(lm.y * h)
                                cv2.circle(rgb_frame, (cx, cy), 1, (0, 255, 0), -1)
                            for idx in L_EYE_INDICES + R_EYE_INDICES:
                                lm = face_landmarks[idx]
                                cx, cy = int(lm.x * w), int(lm.y * h)
                                cv2.circle(rgb_frame, (cx, cy), 3, (0, 0, 255), -1)
                        
                        frame_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
                        time.sleep(0.03)
            except Exception as e:
                st.error(f"Ошибка: {e}")
            finally:
                cap.release()
