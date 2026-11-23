from collections import deque
from datetime import datetime

FLAT_THRESHOLD = 0.5
WINDOW = 5


class TrendTracker:
    def __init__(self):
        self.window = deque(maxlen=WINDOW)
        self.last_ts = None
        self.last_avg = None

    def update(self, record):
        ts = datetime.strptime(record['ts'], '%Y-%m-%d %H:%M:%S')
        self.window.append(record['value'])
        avg = sum(self.window) / len(self.window)
        if self.last_ts is None:
            self.last_ts, self.last_avg = ts, avg
            return 'flat'
        minutes = (ts - self.last_ts).total_seconds() / 60
        change = (avg - self.last_avg) / minutes
        self.last_ts, self.last_avg = ts, avg
        if change > FLAT_THRESHOLD:
            return 'rising'
        if change < -FLAT_THRESHOLD:
            return 'falling'
        return 'flat'
