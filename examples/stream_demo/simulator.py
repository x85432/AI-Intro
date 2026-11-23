import json
import time

from trend import TrendTracker


def main():
    rows = json.load(open('fixtures/readings.json'))
    tracker = TrendTracker()
    for row in rows:
        print(row['ts'], row['value'], tracker.update(row))
        time.sleep(1)


if __name__ == '__main__':
    main()
