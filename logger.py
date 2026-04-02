"""
Emotion Logger
Dual storage: SQLite + CSV
"""

import sqlite3
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict


DB_PATH  = os.path.join('logs', 'emotion_db.sqlite')
CSV_PATH = os.path.join('logs', 'emotion_log.csv')


class EmotionLogger:
    def __init__(self):
        os.makedirs('logs', exist_ok=True)
        self._init_db()
        self._init_csv()

    # ──────────────────────────────────────────
    # Init
    # ──────────────────────────────────────────

    def _init_db(self):
        with self._conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp  TEXT    NOT NULL,
                    face_id    INTEGER NOT NULL,
                    emotion    TEXT    NOT NULL,
                    confidence REAL    NOT NULL,
                    session_id TEXT    NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ts ON detections(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_emo ON detections(emotion)')

    def _init_csv(self):
        if not os.path.exists(CSV_PATH):
            with open(CSV_PATH, 'w', newline='') as f:
                csv.writer(f).writerow(
                    ['id', 'timestamp', 'face_id', 'emotion', 'confidence', 'session_id']
                )

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    # ──────────────────────────────────────────
    # Write
    # ──────────────────────────────────────────

    def log(self, result: dict):
        ts         = datetime.now().isoformat()
        face_id    = result.get('face_id', 0)
        emotion    = result.get('emotion', 'unknown')
        confidence = float(result.get('confidence', 0))
        session_id = datetime.now().strftime('%Y%m%d_%H')

        # SQLite
        with self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO detections (timestamp, face_id, emotion, confidence, session_id) '
                'VALUES (?, ?, ?, ?, ?)',
                (ts, face_id, emotion, confidence, session_id)
            )
            row_id = cur.lastrowid

        # CSV (append)
        with open(CSV_PATH, 'a', newline='') as f:
            csv.writer(f).writerow([row_id, ts, face_id, emotion, confidence, session_id])

    # ──────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────

    def get_logs(self, limit: int = 50) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT id, timestamp, face_id, emotion, confidence, session_id '
                'FROM detections ORDER BY id DESC LIMIT ?', (limit,)
            ).fetchall()

        return [
            {'id': r[0], 'timestamp': r[1], 'face_id': r[2],
             'emotion': r[3], 'confidence': r[4], 'session_id': r[5]}
            for r in rows
        ]

    def get_stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute('SELECT COUNT(*) FROM detections').fetchone()[0]

            counts_rows = conn.execute(
                'SELECT emotion, COUNT(*) FROM detections GROUP BY emotion'
            ).fetchall()
            counts = {r[0]: r[1] for r in counts_rows}

            conf_rows = conn.execute(
                'SELECT emotion, AVG(confidence) FROM detections GROUP BY emotion'
            ).fetchall()
            avg_conf = {r[0]: round(r[1], 1) for r in conf_rows}

            latest_row = conn.execute(
                'SELECT emotion, confidence FROM detections ORDER BY id DESC LIMIT 1'
            ).fetchone()

        dominant = max(counts, key=counts.get) if counts else 'none'

        return {
            'total_detections': total,
            'emotion_counts':   counts,
            'avg_confidence':   avg_conf,
            'dominant_emotion': dominant,
            'latest_emotion':   latest_row[0] if latest_row else 'none',
            'latest_confidence':latest_row[1] if latest_row else 0,
        }

    def get_timeline(self, minutes: int = 5) -> list:
        """Returns per-second emotion counts for the last N minutes."""
        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        with self._conn() as conn:
            rows = conn.execute(
                'SELECT timestamp, emotion FROM detections WHERE timestamp > ? ORDER BY timestamp',
                (since,)
            ).fetchall()

        # Bucket by second
        buckets = defaultdict(lambda: defaultdict(int))
        for ts_str, emotion in rows:
            try:
                second = ts_str[:19]   # YYYY-MM-DDTHH:MM:SS
                buckets[second][emotion] += 1
            except Exception:
                pass

        return [
            {'time': ts, 'emotions': dict(counts)}
            for ts, counts in sorted(buckets.items())
        ]

    # ──────────────────────────────────────────
    # Clear
    # ──────────────────────────────────────────

    def clear(self):
        with self._conn() as conn:
            conn.execute('DELETE FROM detections')

        with open(CSV_PATH, 'w', newline='') as f:
            csv.writer(f).writerow(
                ['id', 'timestamp', 'face_id', 'emotion', 'confidence', 'session_id']
            )
