"""
Alert System
Fires alerts when emotions exceed confidence/duration thresholds.
"""

import time


class AlertSystem:
    def __init__(self):
        # emotion → {confidence %, sustained seconds}
        self.thresholds = {
            'angry':   {'confidence': 75, 'duration': 3},
            'fear':    {'confidence': 70, 'duration': 3},
            'sad':     {'confidence': 80, 'duration': 5},
            'disgust': {'confidence': 75, 'duration': 4},
        }
        self._start_times: dict = {}

    def check(self, results: list) -> list:
        alerts = []
        now    = time.time()

        seen_keys = set()
        for r in results:
            emotion    = r.get('emotion', '')
            confidence = r.get('confidence', 0)
            face_id    = r.get('face_id', 0)
            key        = f"{face_id}_{emotion}"
            seen_keys.add(key)

            if emotion not in self.thresholds:
                continue

            thresh = self.thresholds[emotion]
            if confidence >= thresh['confidence']:
                if key not in self._start_times:
                    self._start_times[key] = now
                duration = now - self._start_times[key]

                if duration >= thresh['duration']:
                    alerts.append({
                        'type':       'emotion_alert',
                        'emotion':    emotion,
                        'face_id':    face_id,
                        'confidence': confidence,
                        'duration':   round(duration, 1),
                        'level':      'danger' if emotion in ('angry', 'fear') else 'warning',
                        'message':    (
                            f"⚠️  Face #{face_id}: {emotion.upper()} detected "
                            f"for {round(duration,1)}s at {confidence}%"
                        )
                    })
            else:
                self._start_times.pop(key, None)

        # Clean up stale trackers for faces that disappeared
        for key in list(self._start_times.keys()):
            if key not in seen_keys:
                del self._start_times[key]

        return alerts

    def update_thresholds(self, new_thresholds: dict):
        for emotion, config in new_thresholds.items():
            if emotion in self.thresholds:
                self.thresholds[emotion].update(config)
            else:
                self.thresholds[emotion] = config

    def reset(self):
        self._start_times.clear()
