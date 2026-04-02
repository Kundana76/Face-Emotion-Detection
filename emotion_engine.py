"""
Emotion Detection Engine
Supports: FER (primary) → DeepFace → OpenCV (fallback)
"""

import cv2
import numpy as np
from datetime import datetime

# Emotion → display color (BGR)
EMOTION_COLORS = {
    'happy':    (0,   220, 255),   # gold
    'sad':      (255, 130,  50),   # blue
    'angry':    (50,   50, 255),   # red
    'surprise': (50,  200, 255),   # orange
    'fear':     (200,  50, 200),   # purple
    'disgust':  (50,  200, 100),   # green
    'neutral':  (160, 160, 160),   # gray
}

EMOTION_EMOJIS = {
    'happy': '😊', 'sad': '😢', 'angry': '😠',
    'surprise': '😲', 'fear': '😨', 'disgust': '🤢', 'neutral': '😐'
}


class EmotionEngine:
    def __init__(self):
        self.frame_skip  = 3        # process every Nth frame
        self._counter    = 0
        self._cached     = []
        self.mode        = 'none'
        self._detector   = None
        self._cascade    = None
        self._load_detector()

    # ──────────────────────────────────────────
    # Loader — tries best available library
    # ──────────────────────────────────────────

    def _load_detector(self):
        # Try FER first
        try:
            from fer import FER
            self._detector = FER(mtcnn=False)
            self.mode = 'fer'
            print("✅  Emotion engine: FER loaded")
            return
        except Exception as e:
            print(f"⚠️   FER not available ({e})")

        # Try DeepFace
        try:
            from deepface import DeepFace
            self._detector = DeepFace
            self.mode = 'deepface'
            print("✅  Emotion engine: DeepFace loaded")
            return
        except Exception as e:
            print(f"⚠️   DeepFace not available ({e})")

        # Fallback: OpenCV haarcascade
        self.mode    = 'opencv'
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        print("⚠️   Emotion engine: OpenCV fallback (install 'fer' for real detection)")

    # ──────────────────────────────────────────
    # Public detect
    # ──────────────────────────────────────────

    def detect(self, frame, force=False):
        self._counter += 1

        # Honour frame-skip unless forced (image upload)
        if not force and (self._counter % self.frame_skip != 0):
            return self._cached

        try:
            if   self.mode == 'fer':      results = self._detect_fer(frame)
            elif self.mode == 'deepface': results = self._detect_deepface(frame)
            else:                         results = self._detect_opencv(frame)
        except Exception as exc:
            print(f"Detection error: {exc}")
            results = []

        self._cached = results
        return results

    # ──────────────────────────────────────────
    # Backend implementations
    # ──────────────────────────────────────────

    def _detect_fer(self, frame):
        detections = self._detector.detect_emotions(frame)
        results = []
        for i, d in enumerate(detections):
            box      = d['box']
            emotions = d['emotions']
            dominant = max(emotions, key=emotions.get)
            results.append(self._make_result(
                face_id   = i + 1,
                box       = {'x': int(box[0]), 'y': int(box[1]),
                             'w': int(box[2]), 'h': int(box[3])},
                dominant  = dominant,
                confidence= round(emotions[dominant] * 100, 1),
                all_emo   = {k: round(v * 100, 1) for k, v in emotions.items()}
            ))
        return results

    def _detect_deepface(self, frame):
        try:
            analysis = self._detector.analyze(
                frame,
                actions           = ['emotion'],
                enforce_detection = False,
                detector_backend  = 'opencv',
                silent            = True
            )
            if isinstance(analysis, dict):
                analysis = [analysis]

            results = []
            for i, a in enumerate(analysis):
                emo_scores = a.get('emotion', {})
                dominant   = a.get('dominant_emotion', 'neutral')
                region     = a.get('region', {'x': 0, 'y': 0, 'w': 100, 'h': 100})
                results.append(self._make_result(
                    face_id   = i + 1,
                    box       = {'x': int(region.get('x', 0)),
                                 'y': int(region.get('y', 0)),
                                 'w': int(region.get('w', 100)),
                                 'h': int(region.get('h', 100))},
                    dominant  = dominant,
                    confidence= round(float(emo_scores.get(dominant, 0)), 1),
                    all_emo   = {k: round(float(v), 1) for k, v in emo_scores.items()}
                ))
            return results
        except Exception:
            return []

    def _detect_opencv(self, frame):
        """Fallback: face detection only with demo emotion scores."""
        import random
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        EMOS  = ['happy', 'neutral', 'sad', 'angry', 'surprise', 'fear', 'disgust']
        results = []
        for i, (x, y, w, h) in enumerate(faces):
            # Deterministic-ish from face position for stability
            seed  = int(x + y + w + h)
            rng   = random.Random(seed // 10)
            picks = rng.choices(EMOS, weights=[40,25,10,8,8,5,4], k=1)
            dom   = picks[0]
            conf  = round(rng.uniform(65, 92), 1)
            all_e = {e: round(rng.uniform(0, 15), 1) for e in EMOS}
            all_e[dom] = conf
            results.append(self._make_result(
                face_id   = i + 1,
                box       = {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                dominant  = dom,
                confidence= conf,
                all_emo   = all_e
            ))
        return results

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _make_result(face_id, box, dominant, confidence, all_emo):
        return {
            'face_id':      face_id,
            'box':          box,
            'emotion':      dominant,
            'confidence':   confidence,
            'all_emotions': all_emo,
            'emoji':        EMOTION_EMOJIS.get(dominant, '😐'),
            'timestamp':    datetime.now().isoformat()
        }

    def draw_results(self, frame, results):
        """Annotate frame with bounding boxes and labels."""
        for r in results:
            box  = r['box']
            x, y, w, h = box['x'], box['y'], box['w'], box['h']
            emo  = r['emotion']
            conf = r['confidence']
            col  = EMOTION_COLORS.get(emo, (200, 200, 200))

            # Bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), col, 2)

            # Label background + text
            label = f"{emo.upper()}  {conf}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, max(y-th-12, 0)), (x+tw+12, y), col, -1)
            cv2.putText(frame, label, (x+6, max(y-4, th)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # Face ID badge
            cv2.putText(frame, f"#{r['face_id']}",
                        (x+4, y+h-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        return frame
