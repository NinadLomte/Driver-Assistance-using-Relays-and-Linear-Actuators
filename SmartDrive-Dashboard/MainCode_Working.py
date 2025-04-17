from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
import threading
import cv2
import torch
from picamera2 import Picamera2
from ultralytics import YOLO
import RPi.GPIO as GPIO
import time
import os
from datetime import datetime
import csv
from io import StringIO
from functools import wraps

# Headless mode configuration
os.environ['DISPLAY'] = ':0'
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Credentials
VALID_USERNAME = "ninad"
VALID_PASSWORD = "ninad"

# Initialize camera
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "RGB888"},
    controls={"FrameRate": 30}
)
picam2.configure(config)
picam2.start()

# Load YOLO model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = YOLO('yolov8n.pt').to(device)
model.half()

# GPIO Setup
relay_pins = {"relay1": 17, "relay2": 18, "relay3": 22, "relay4": 23}
GPIO.setmode(GPIO.BCM)
for pin in relay_pins.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

# Shared resources
current_state = "idle"
frame = None
detection_result = []
detection_log = []
frame_lock = threading.Lock()
detection_lock = threading.Lock()
log_lock = threading.Lock()

CRITICAL_CLASSES = ['person', 'car', 'truck', 'motorcycle', 'bicycle']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def stop():
    for pin in relay_pins.values():
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.1)

def accelerate():
    global current_state
    if current_state == "accelerate":
        return
    
    stop()
    GPIO.output(relay_pins["relay1"], GPIO.LOW)
    GPIO.output(relay_pins["relay3"], GPIO.LOW)
    GPIO.output(relay_pins["relay2"], GPIO.HIGH)
    GPIO.output(relay_pins["relay4"], GPIO.HIGH)
    time.sleep(5)
    current_state = "accelerate"
    

def brake():
    global current_state
    if current_state == "brake":
        return
    
    stop()
    GPIO.output(relay_pins["relay1"], GPIO.HIGH)
    GPIO.output(relay_pins["relay3"], GPIO.HIGH)
    GPIO.output(relay_pins["relay2"], GPIO.LOW)
    GPIO.output(relay_pins["relay4"], GPIO.LOW)
    current_state = "brake"
    time.sleep(5)

def camera_thread():
    global frame
    while True:
        try:
            # Capture raw frame
            img = picam2.capture_array()
            
            # Store raw frame
            with frame_lock:
                frame = img.copy()
        except Exception as e:
            print(f"Camera error: {e}")

def detection_thread():
    global detection_result, detection_log
    frame_count = 0
    
    while True:
        try:
            # Get the latest frame
            with frame_lock:
                if frame is None:
                    time.sleep(0.1)
                    continue
                img = frame.copy()
            
            # Process every 3rd frame for detection
            if frame_count % 3 == 0:
                results = model.predict(img, conf=0.25)
                
                filtered_detections = []
                log_entries = []
                timestamp = datetime.now().isoformat()
                
                for box in results[0].boxes:
                    data = box.data.tolist()[0]
                    if len(data) >= 6:
                        class_id = int(data[5])
                        class_name = model.names[class_id]
                        
                        if class_name in CRITICAL_CLASSES:
                            filtered_detections.append({
                                'label': class_name,
                                'confidence': float(data[4])
                            })
                            log_entries.append({
                                'timestamp': timestamp,
                                'label': class_name,
                                'confidence': float(data[4])
                            })

                with detection_lock, log_lock:
                    detection_result = filtered_detections
                    if log_entries:
                        detection_log.extend(log_entries)

                # Control logic
                brake() if filtered_detections else accelerate()
            
            frame_count += 1
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Detection error: {e}")
            time.sleep(1)

# Start threads
threading.Thread(target=camera_thread, daemon=True).start()
threading.Thread(target=detection_thread, daemon=True).start()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('SmartDrive.html')

@app.route('/video_feed')
@login_required
def video_feed():
    def generate():
        while True:
            with frame_lock:
                if frame is None:
                    continue
                # Convert raw frame to JPEG (no detection boxes)
                ret, jpeg = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   jpeg.tobytes() + b'\r\n')
    
    return Response(generate(),
                  mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/detections')
def detections():
    with detection_lock:
        return jsonify(detection_result)

@app.route('/download_log')
@login_required
def download_log():
    with log_lock:
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Timestamp', 'Object', 'Confidence'])
        for entry in detection_log:
            cw.writerow([
                entry['timestamp'],
                entry['label'],
                entry['confidence']
            ])
    
    return Response(
        si.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=detection_log.csv'}
    )

@app.route('/status')
@login_required
def status():
    return {'state': current_state}

@app.route('/control/<command>')
@login_required
def control(command):
    if command == 'stop':
        stop()
    elif command == 'accelerate':
        accelerate()
    elif command == 'brake':
        brake()
    return '', 204

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        stop()
        GPIO.cleanup()