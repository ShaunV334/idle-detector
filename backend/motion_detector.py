import sys
import subprocess
from pathlib import Path
import os
import time
from flask import Flask, Response
from flask_cors import CORS

# -------------------------------
# 🧩  Virtual environment check
# -------------------------------
def check_venv():
    if getattr(sys, 'base_prefix', sys.prefix) == sys.prefix:
        print("❌ Not running inside a virtual environment!")
        print("Please activate the venv first:")
        print("   venv\\Scripts\\activate   (Windows)")
        print("or source venv/bin/activate (Linux/macOS)")
        sys.exit(1)

check_venv()

# -------------------------------
# 📦 Dependency management
# -------------------------------
required_packages = {
    'opencv-python': 'cv2',
    'ultralytics': 'ultralytics',
    'numpy': 'numpy',
    'firebase-admin': 'firebase_admin',
    'python-dotenv': 'dotenv',
    'flask': 'flask',
    'flask-cors': 'flask_cors'
}

def install_package(package):
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"⚠️ Failed to install {package}. Try manually: pip install {package}")
        return False

for pkg, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"✓ {pkg} is installed")
    except ImportError:
        if not install_package(pkg):
            sys.exit(1)

# -------------------------------
# 🌍 Imports after install
# -------------------------------
from dotenv import load_dotenv
import cv2
import numpy as np
from ultralytics import YOLO
import firebase_admin
from firebase_admin import credentials, db

# -------------------------------
# 🔐 Firebase setup
# -------------------------------
load_dotenv()
config_dir = Path("../config")
config_dir.mkdir(exist_ok=True)

try:
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    db_url = os.getenv('FIREBASE_DATABASE_URL')
    if not cred_path or not db_url:
        raise ValueError("Missing FIREBASE_CREDENTIALS_PATH or FIREBASE_DATABASE_URL")

    cred_path = Path(cred_path)
    if not cred_path.is_file():
        print(f"❌ Firebase credentials not found at {cred_path}")
        sys.exit(1)

    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    print("✅ Firebase initialized successfully")

except Exception as e:
    print(f"Firebase initialization failed: {e}")
    sys.exit(1)

# -------------------------------
# 🎥 Motion Detector Class
# -------------------------------
class MotionDetector:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            raise RuntimeError("Camera not detected. Check your webcam connection.")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.prev_frame = None
        self.motion_threshold = 30
        self.last_state = (None, None)
        self.last_update = 0
        self.update_interval = 2  # seconds between Firebase writes

    def detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
            return False, False

        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        motion_detected = np.mean(thresh) > self.motion_threshold

        results = self.model(frame)
        humans_detected = any(cls == 0 for cls in results[0].boxes.cls.cpu().numpy())

        now = time.time()
        current_state = (motion_detected, humans_detected)

        if current_state != self.last_state or now - self.last_update > self.update_interval:
            try:
                ref = db.reference('detection_status')
                ref.set({
                    'motion_detected': bool(motion_detected),
                    'humans_present': bool(humans_detected),
                    'timestamp': {'.sv': 'timestamp'}
                })
                print(f"[Firebase] Motion={motion_detected}, Humans={humans_detected}")
            except Exception as e:
                print(f"⚠️ Firebase update failed: {e}")

            self.last_update = now
            self.last_state = current_state

        self.prev_frame = gray
        return motion_detected, humans_detected

# -------------------------------
# 🌐 Flask App for Streaming
# -------------------------------
app = Flask(__name__)
CORS(app)
detector = MotionDetector()

def generate_frames():
    while True:
        success, frame = detector.cap.read()
        if not success:
            break

        motion, humans = detector.detect_motion(frame)
        label = f"Motion: {'Yes' if motion else 'No'} | Humans: {'Yes' if humans else 'No'}"
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0) if humans or motion else (0,0,255), 2)

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# -------------------------------
# 🚀 Main entry
# -------------------------------
if __name__ == "__main__":
    print("🚀 Starting Flask video stream at http://localhost:5000/video_feed")
    app.run(host='0.0.0.0', port=5000)
