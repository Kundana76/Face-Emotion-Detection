# 🧠 FEIS — Face Emotion Intelligence System

A real-time multi-face emotion detection and analytics platform built with Flask + OpenCV.

---

## 🚀 Quick Start (VS Code)

### 1 — Prerequisites
- Python 3.10 or 3.11 (recommended)
- pip (comes with Python)
- A webcam (optional — you can also upload images)

### 2 — Setup (run these in your VS Code terminal)

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

> ⏳ **Note:** `fer` installs TensorFlow (~500 MB). This may take 5–10 minutes on first install.

### 3 — Run the server

```bash
python app.py
```

### 4 — Open in browser

```
http://localhost:5000
```

---

## 📁 Project Structure

```
FEIS/
├── app.py                  ← Flask server (entry point)
├── requirements.txt
├── README.md
├── .env.example
│
├── core/
│   ├── emotion_engine.py   ← FER / DeepFace / OpenCV detection
│   ├── logger.py           ← SQLite + CSV dual logging
│   ├── alert_system.py     ← Threshold-based alerts
│   └── report_generator.py ← PDF report generation
│
├── templates/
│   └── index.html          ← Dashboard UI
│
├── static/
│   ├── css/style.css       ← Dark theme styles
│   └── js/dashboard.js     ← Webcam + charts + API calls
│
├── logs/                   ← Auto-created: emotion_db.sqlite + emotion_log.csv
└── reports/                ← Auto-created: generated PDF reports
```

---

## 🎯 Features

| Feature | Details |
|---|---|
| **Webcam detection** | Live multi-face emotion detection |
| **Image upload** | Analyze any photo |
| **7 emotions** | Happy, Sad, Angry, Surprise, Fear, Disgust, Neutral |
| **Real-time bars** | Confidence % for each emotion, updates live |
| **Timeline chart** | Emotion trends over session |
| **Pie chart** | Session emotion distribution |
| **Dual logging** | SQLite database + CSV file |
| **Alert system** | Triggers on sustained anger/fear/sadness |
| **PDF reports** | One-click professional report download |
| **Settings panel** | Adjust frame skip, detection interval, thresholds |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/detect` | Send base64 webcam frame, get emotion JSON |
| POST | `/api/detect-image` | Upload image file, get annotated result |
| GET | `/api/stats` | Session statistics + timeline |
| GET | `/api/logs?limit=50` | Recent detection log |
| DELETE | `/api/logs` | Clear all logs |
| GET | `/api/report` | Download PDF report |
| GET | `/api/config` | Get current configuration |
| POST | `/api/config` | Update settings |

---

## ⚙️ Emotion Detection Engines

FEIS auto-detects the best available library:

1. **FER** (default) — Simple, accurate, uses a pre-trained CNN on FER2013
2. **DeepFace** — More backends available; install with `pip install deepface`
3. **OpenCV fallback** — Face detection only (demo mode, no real emotion model)

---

## 🛠 Troubleshooting

**Camera not working?**
- Make sure your browser has camera permission
- Try a different browser (Chrome recommended)
- Use the image upload feature instead

**`fer` installation fails?**
- Try: `pip install fer --no-deps` then install deps manually
- Or use DeepFace: `pip install deepface` (comment out `fer` in requirements.txt)

**Slow detection?**
- Increase Frame Skip in Settings (e.g., 5 or 10)
- Increase Detection Interval to 500ms+
- Use a GPU if available

**Port already in use?**
- Change the port in `app.py`: `app.run(port=5001)`

---

## 📄 License
MIT — Free for personal and commercial use.
