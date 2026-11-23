from datetime import datetime


class TrendTracker:
    def __init__(self):
        self.last = None

    def update(self, record):
        ts = datetime.strptime(record['ts'], '%Y-%m-%d %H:%M:%S')
        value = record['value']
        if self.last is None:
            self.last = (ts, value)
            return 'flat'
        diff = value - self.last[1]
        self.last = (ts, value)
        if diff > 0.5:
            return 'rising'
        if diff < -0.5:
            return 'falling'
        return 'flat'
