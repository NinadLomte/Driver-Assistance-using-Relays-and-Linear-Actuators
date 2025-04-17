# SmartDrive Dashboard 🚗📡

SmartDrive is an intelligent vehicle monitoring dashboard built using Flask, YOLOv8, Raspberry Pi Camera, and ultrasonic sensors. It provides live video feeds, real-time object detection, distance monitoring, GPS mapping, and system logging – all through a sleek dashboard interface.

## 📸 Features

- Live camera feed from Raspberry Pi
- YOLOv8 object detection (person, car, truck, etc.)
- Distance measurement using ultrasonic sensors
- Real-time car status (idle, accelerate, brake)
- System event logging & detection logs export
- Live GPS tracking via Google Maps
- Responsive UI built with Tailwind CSS

## 🛠️ Requirements

- Raspberry Pi OS
- Python 3.7+
- picamera2
- OpenCV
- Flask
- YOLOv8 (via `ultralytics`)
- GPIO support

## 🔧 Setup Instructions

1. **Clone the repo**
    ```bash
    git clone https://github.com/yourusername/SmartDrive-Dashboard.git
    cd SmartDrive-Dashboard
    ```

2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Run the app**
    ```bash
    sudo python3 MainCode_Working.py
    ```

4. **Access the dashboard**
    Open your browser and go to: `http://<raspberry-pi-ip>:5000`

## 🧠 Authentication

- Username: `ninad`
- Password: `ninad`

> Update the credentials in `MainCode_Working.py` for better security.

## 🗂️ File Overview

| File | Description |
|------|-------------|
| `MainCode_Working.py` | Main Flask app with camera and GPIO logic |
| `templates/SmartDrive.html` | Frontend dashboard with Tailwind styling |
| `requirements.txt` | Python dependencies |

## 🧾 License

MIT License. Feel free to fork and contribute!
