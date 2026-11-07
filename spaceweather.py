"""Fixed NOAA sources, short request timeouts, timestamped ten-minute cache."""
import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.request import Request, urlopen

SOURCES = {
    'kp': ('https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json', 'Kp'),
    'flux': ('https://services.swpc.noaa.gov/json/f107_cm_flux.json', 'flux'),
}


def latest(data, field):
    if data and isinstance(data[0], list):
        data = [dict(zip(data[0], row)) for row in data[1:]]
    rows = []
    for row in data:
        try:
            value = float(row[field])
            stamp = datetime.fromisoformat(row['time_tag'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if math.isfinite(value) and value >= 0:
                rows.append((stamp, value))
        except (ValueError, TypeError, KeyError):
            continue
    if not rows:
        raise ValueError('No valid timestamped observations in source.')
    stamp, value = max(rows)
    return {'value': value, 'observed_at': stamp.isoformat()}


class SpaceWeather:
    def __init__(self):
        self.lock = threading.Lock()
        self.cached = None
        self.expiry = 0

    def fetch_one(self, name):
        url, field = SOURCES[name]
        try:
            with urlopen(Request(url, headers={'User-Agent': 'SignalPier/0.1'}), timeout=5) as response:
                payload = response.read(2_000_001)
                if len(payload) > 2_000_000:
                    raise ValueError('Source response exceeds limit.')
                result = latest(json.loads(payload), field)
            return name, dict(result, source=url, error=None)
        except Exception as exc:
            return name, {'value': None, 'observed_at': None, 'source': url, 'error': str(exc)}

    def get(self):
        with self.lock:
            if self.cached is not None and time.monotonic() < self.expiry:
                return self.cached
            with ThreadPoolExecutor(max_workers=2) as pool:
                readings = dict(pool.map(self.fetch_one, SOURCES))
            self.cached = dict(readings, fetched_at=datetime.now(timezone.utc).isoformat())
            self.expiry = time.monotonic() + (600 if all(r['error'] is None for r in readings.values()) else 60)
            return self.cached
