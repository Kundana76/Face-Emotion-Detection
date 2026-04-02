"""
FEIS — Face Emotion Intelligence System
Main Flask Application
Run: python app.py
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import base64
import numpy as np
import cv2
from datetime import datetime
import os

from core.emotion_engine import EmotionEngine
from core.logger import EmotionLogger
from core.alert_system import AlertSystem
from core.report_generator import ReportGenerator

app = Flask(__name__)
CORS(app)

# Initialize all components
print("🧠 Initializing FEIS components...")
emotion_engine  = EmotionEngine()
emotion_logger  = EmotionLogger()
alert_system    = AlertSystem()
report_gen      = ReportGenerator()
print("✅ All components ready!")


# ─────────────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ─────────────────────────────────────────────────
# API: DETECTION (live webcam frames)
# ─────────────────────────────────────────────────

@app.route('/api/detect', methods=['POST'])
def detect_emotion():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400

        # Decode base64 image from browser
        img_b64 = data['image']
        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]

        img_bytes = base64.b64decode(img_b64)
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'error': 'Could not decode image'}), 400

        # Run detection
        results = emotion_engine.detect(frame)

        # Log every detected face
        for result in results:
            emotion_logger.log(result)

        # Check alert thresholds
        alerts = alert_system.check(results)

        return jsonify({
            'success':    True,
            'results':    results,
            'alerts':     alerts,
            'face_count': len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────
# API: DETECTION (uploaded image file)
# ─────────────────────────────────────────────────

@app.route('/api/detect-image', methods=['POST'])
def detect_from_upload():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file      = request.files['image']
        img_bytes = file.read()
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'error': 'Invalid image file'}), 400

        results = emotion_engine.detect(frame, force=True)

        for result in results:
            emotion_logger.log(result)

        # Return annotated image as base64
        annotated = emotion_engine.draw_results(frame.copy(), results)
        _, buffer  = cv2.imencode('.jpg', annotated)
        img_b64    = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'success':          True,
            'results':          results,
            'annotated_image':  f'data:image/jpeg;base64,{img_b64}',
            'face_count':       len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────
# API: ANALYTICS
# ─────────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        return jsonify({
            'success':  True,
            'stats':    emotion_logger.get_stats(),
            'timeline': emotion_logger.get_timeline()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        limit = int(request.args.get('limit', 50))
        return jsonify({'success': True, 'logs': emotion_logger.get_logs(limit)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    try:
        emotion_logger.clear()
        alert_system.reset()
        return jsonify({'success': True, 'message': 'All logs cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────
# API: REPORT
# ─────────────────────────────────────────────────

@app.route('/api/report', methods=['GET'])
def download_report():
    try:
        stats    = emotion_logger.get_stats()
        logs     = emotion_logger.get_logs(100)
        timeline = emotion_logger.get_timeline()

        path = report_gen.generate(stats, logs, timeline)

        return send_file(
            path,
            as_attachment=True,
            download_name=f'FEIS_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────
# API: CONFIG
# ─────────────────────────────────────────────────

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'thresholds':  alert_system.thresholds,
        'frame_skip':  emotion_engine.frame_skip,
        'detector':    emotion_engine.mode
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        data = request.get_json()
        if 'thresholds' in data:
            alert_system.update_thresholds(data['thresholds'])
        if 'frame_skip' in data:
            emotion_engine.frame_skip = max(1, int(data['frame_skip']))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🚀  FEIS — Face Emotion Intelligence System")
    print("  📊  Dashboard → http://localhost:5000")
    print("  📡  API Base  → http://localhost:5000/api/")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
