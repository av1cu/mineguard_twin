import cv2
import sys
import os
import urllib.request

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
except ImportError:
    print("Error: mediapipe is not installed. Run: pip install mediapipe opencv-python")
    sys.exit(1)

def download_model_if_needed():
    model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "face_landmarker.task")
    
    if not os.path.exists(model_path):
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        print(f"Downloading MediaPipe Face Landmarker task model from {url}...")
        try:
            urllib.request.urlretrieve(url, model_path)
            print("Download completed successfully!")
        except Exception as e:
            print(f"Error downloading model: {e}")
            sys.exit(1)
            
    return model_path

def run_face_landmark_demo():
    model_path = download_model_if_needed()

    print("Initializing Face Landmarker Tasks API...")
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1
    )

    print("Opening camera (press ESC or 'q' to quit)...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit(1)

    # Configure Face Landmarker with options
    with vision.FaceLandmarker.create_from_options(options) as landmarker:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Error: Frame capture failed.")
                break

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to MediaPipe Image format
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Process frame
            results = landmarker.detect(mp_image)

            # Draw landmarks manually
            h, w, _ = frame.shape
            if results.face_landmarks:
                for face_landmarks in results.face_landmarks:
                    for lm in face_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        # Draw small green circle on each landmark point
                        cv2.circle(frame, (cx, cy), 1, (0, 255, 0), -1)

            # Display window
            cv2.imshow("MineGuard Driver Face Landmark Detection (Tasks API)", frame)

            # Exit key listeners
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'): # ESC or 'q'
                break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera released. Demo closed.")

if __name__ == "__main__":
    run_face_landmark_demo()
