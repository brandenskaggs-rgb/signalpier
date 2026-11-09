"""SignalPier: local, bounded receiver jobs; Python 3.10+ stdlib only."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import platform
import random
import secrets
import shutil
import statistics
import subprocess
import tempfile
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from spaceweather import SpaceWeather
from updates import UpdateChecker, installer_status, request_install
from receivers import ReceiverMonitor, inspect_receiver

STATIC = Path(__file__).parent / "static"
MAX_BODY = 1_000_000


def number(data, key, default, low, high):
    value = float(data.get(key, default))
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}.")
    return value


def settings(data):
    mode = data.get("mode", "demo")
    kind = data.get("kind", "scan")
    if mode not in ("demo", "hardware") or kind not in ("scan", "decode"):
        raise ValueError("Choose demo/hardware and scan/decode.")
    start = number(data, "start_mhz", 430, 24, 1766)
    end = number(data, "end_mhz", 440, 24, 1766)
    step = number(data, "bin_khz", 25, 5, 1000)
    if end <= start or end - start > 100 or (end - start) * 1000 / step > 4096:
        raise ValueError("Use an increasing span up to 100 MHz and at most 4096 requested bins.")
    device = str(data.get("device", "0"))
    if not device.isascii() or not device.isdigit() or len(device) > 2:
        raise ValueError("Device must be a USB receiver index from 0 to 99.")
    return dict(mode=mode, kind=kind, start_mhz=start, end_mhz=end, bin_khz=step,
                frequency_mhz=number(data, "frequency_mhz", 433.92, 24, 1766),
                duration=int(number(data, "duration", 10, 2, 60)), device=device)


def parse_power(text):
    """Stitch tuning hops by timestamp. Preserve missing/nonfinite bins as gaps."""
    sweeps = {}
    for row in csv.reader(io.StringIO(text)):
        if not row or len(row) < 7:
            continue
        try:
            stamp = f"{row[0].strip()} {row[1].strip()}"
            low, high, step = map(float, row[2:5])
            if not all(math.isfinite(v) for v in (low, high, step)) or step <= 0 or high <= low:
                continue
            points = sweeps.setdefault(stamp, {})
            for index, cell in enumerate(row[6:]):
                freq = low + index * step
                if freq >= high:
                    break
                try:
                    value = float(cell)
                except ValueError:
                    value = float("nan")
                points[freq] = round(value, 2) if math.isfinite(value) else None
        except ValueError:
            continue
    return [dict(timestamp=stamp, points=[[f, v] for f, v in sorted(points.items())])
            for stamp, points in sorted(sweeps.items()) if points][-60:]


def detect_peaks(points, margin=10):
    valid = [p[1] for p in points if p[1] is not None]
    if not valid:
        return []
    floor = statistics.median(valid)
    candidates = []
    for index in range(1, len(points) - 1):
        freq, power = points[index]
        left, right = points[index - 1][1], points[index + 1][1]
        if power is not None and left is not None and right is not None:
            if power > floor + margin and power > left and power >= right:
                candidates.append(dict(frequency_hz=freq, power_db=power,
                                       above_median_db=round(power - floor, 1)))
    return sorted(candidates, key=lambda p: p["power_db"], reverse=True)[:12]


def compact_sweeps(sweeps, max_bins=1024):
    """Preserve strongest bins for plotting while bounding Pi memory/network work."""
    result = []
    for sweep in sweeps[-30:]:
        points = sweep['points']
        stride = max(1, math.ceil(len(points) / max_bins))
        reduced = []
        for start in range(0, len(points), stride):
            bucket = points[start:start + stride]
            valid = [point for point in bucket if point[1] is not None]
            reduced.append(max(valid, key=lambda point: point[1]) if valid else bucket[0])
        result.append(dict(timestamp=sweep['timestamp'], points=reduced))
    return result


def parse_events(text):
    events = deque(maxlen=200)
    for line in text.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
        except json.JSONDecodeError:
            continue
    return list(events)


def command(config):
    if config["kind"] == "scan":
        return ["rtl_power", "-d", config["device"], "-f",
                f'{config["start_mhz"] * 1e6:.0f}:{config["end_mhz"] * 1e6:.0f}:{config["bin_khz"] * 1e3:.0f}',
                "-i", "2", "-e", str(config["duration"]), "-"]
    # Suppress automatic per-user configuration so only these bounded arguments run.
    return ["rtl_433", "-c", "0", "-d", config["device"], "-f",
            f'{config["frequency_mhz"] * 1e6:.0f}', "-s", "250000", "-T",
            str(config["duration"]), "-F", "json", "-M", "time:iso", "-M", "level"]


class Workbench:
    def __init__(self):
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.worker = None
        self.revision = 0
        self.checking = False
        self.state = dict(status="idle", mode="demo", kind=None, message="Choose a receiver task.",
                          sweeps=[], events=[], peaks=[], config=None)

    def snapshot(self, since=None):
        with self.lock:
            if since == self.revision:
                return dict(unchanged=True, revision=self.revision)
            return dict(json.loads(json.dumps(self.state)), revision=self.revision, unchanged=False)

    def update(self, **values):
        with self.lock:
            self.state.update(values)
            self.revision += 1

    def start(self, data):
        config = settings(data)
        with self.lock:
            if self.state["status"] == "running" or self.checking:
                raise RuntimeError("Receiver is busy. Stop the current task first.")
            self.cancel.clear()
            self.revision += 1
            self.state = dict(status="running", mode=config["mode"], kind=config["kind"],
                              message="Collecting a bounded capture…", sweeps=[], events=[], peaks=[], config=config)
        self.worker = threading.Thread(target=self.run, args=(config,), daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel.set()

    def busy(self):
        with self.lock: return self.checking or self.state['status']=='running'

    def test_receiver(self,index):
        with self.lock:
            if self.checking or self.state['status']=='running':
                raise RuntimeError('Finish or stop the capture before testing the receiver.')
            self.checking=True
        try: return dict(inspect_receiver(index),checked_at=time.time())
        finally:
            with self.lock: self.checking=False

    def run(self, config):
        try:
            if config["mode"] == "demo":
                self.demo(config)
            else:
                output = self.capture(command(config), config["duration"] + 15)
                if not self.cancel.is_set():
                    if config["kind"] == "scan":
                        sweeps = parse_power(output)
                        if not sweeps:
                            raise ValueError("Receiver returned no spectrum data. Check the device and driver.")
                        peaks = detect_peaks(sweeps[-1]["points"])
                        self.update(sweeps=compact_sweeps(sweeps), peaks=peaks)
                    else:
                        self.update(events=parse_events(output))
            self.update(status="stopped" if self.cancel.is_set() else "complete",
                        message="Capture stopped." if self.cancel.is_set() else "Capture complete. Results are ready to export.")
        except Exception as exc:
            self.update(status="error", message=str(exc))

    def capture(self, args, timeout):
        binary = shutil.which(args[0])
        if not binary:
            raise ValueError(f"{args[0]} is not installed. Use demo mode or install the Pi receiver packages in README.md.")
        args = [binary, *args[1:]]
        # Files avoid unbounded pipe buffers; output and run time are capped below.
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            proc = subprocess.Popen(args, stdout=output, stderr=errors, stdin=subprocess.DEVNULL,
                                    shell=False)
            deadline = time.monotonic() + timeout
            try:
                while proc.poll() is None:
                    if self.cancel.wait(0.1):
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError("Receiver timed out. Try a narrower frequency span.")
                    if output.seek(0, 2) > 8_000_000 or errors.seek(0, 2) > 1_000_000:
                        raise ValueError("Capture output limit reached. Use a shorter duration.")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)
            errors.seek(0)
            diagnostic = errors.read(4000).decode("utf-8", errors="replace").strip()
            if proc.returncode and not self.cancel.is_set():
                raise ValueError(f"{args[0]} exited with {proc.returncode}: {diagnostic}")
            output.seek(0)
            return output.read(8_000_000).decode("utf-8", errors="replace")

    def demo(self, config):
        rng = random.Random(42)
        sweeps, events = [], []
        count = min(1024, max(16, int((config["end_mhz"] - config["start_mhz"]) * 1000 / config["bin_khz"])))
        for frame in range(config["duration"]):
            if self.cancel.wait(0.25):
                return
            stamp = datetime.now(timezone.utc).isoformat()
            if config["kind"] == "scan":
                points = []
                for index in range(count):
                    x = index / count
                    power = -78 + rng.uniform(-3, 3)
                    for center, height, width in ((0.23, 32, .012), (.53, 23, .022), (.78, 40, .008)):
                        power += height * math.exp(-((x - center) / width) ** 2)
                    freq = (config["start_mhz"] + x * (config["end_mhz"] - config["start_mhz"])) * 1e6
                    points.append([freq, round(power + 2 * math.sin(frame), 2)])
                sweeps.append(dict(timestamp=stamp, points=points))
                self.update(sweeps=list(sweeps), peaks=detect_peaks(points))
            else:
                events.append(dict(time=stamp, model="DEMO weather sensor", id=101,
                                   temperature_C=round(21 + rng.random(), 1), humidity=48,
                                   frequency_mhz=config["frequency_mhz"], simulated=True))
                self.update(events=list(events))


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.workbench = Workbench()
        self.weather = SpaceWeather()
        self.updates = UpdateChecker()
        self.receivers = ReceiverMonitor()
        self.token = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type="application/json"):
        payload = json.dumps(body, allow_nan=False).encode() if content_type == "application/json" else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        return self.headers.get("Host", "") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {"error": "Use localhost or an SSH tunnel."})
        path = urlparse(self.path).path
        if path == "/api/status":
            revision = parse_qs(urlparse(self.path).query).get('revision', [''])[0]
            since = int(revision) if revision.isdigit() else None
            return self.reply(200, dict(**self.server.workbench.snapshot(since), token=self.server.token,
                              platform=platform.machine(), portable=bool(os.environ.get('SIGNALPIER_PORTABLE')), tools={name: bool(shutil.which(name)) for name in ("rtl_power", "rtl_433", "rnsd", "direwolf")}))
        if path == "/api/export":
            return self.reply(200, self.server.workbench.snapshot())
        if path == '/api/receivers':
            active=self.server.workbench.busy()
            force=parse_qs(urlparse(self.path).query).get('refresh')==['1']
            info=self.server.receivers.peek() if active else self.server.receivers.scan(force)
            return self.reply(200,dict(info,active=active))
        if path == "/api/spaceweather":
            return self.reply(200, self.server.weather.get())
        if path == "/api/update":
            return self.reply(200, dict(self.server.updates.check(), installer=installer_status()))
        files = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                 "/crypto.js": ("crypto.js", "text/javascript; charset=utf-8"),
                 "/hamclock.js": ("hamclock.js", "text/javascript; charset=utf-8"),
                 "/solar.js": ("solar.js", "text/javascript; charset=utf-8"),
                 "/world.json": ("world.json", "application/geo+json"),
                 "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path not in files:
            return self.reply(404, {"error": "Not found"})
        name, content_type = files[path]
        self.reply(200, (STATIC / name).read_bytes(), content_type)

    def do_POST(self):
        if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-Workbench-Token", ""), self.server.token):
            return self.reply(403, {"error": "Refresh the workbench before starting a task."})
        origin = self.headers.get("Origin")
        if origin and origin != f'http://{self.headers.get("Host")}':
            return self.reply(403, {"error": "Origin mismatch."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= MAX_BODY:
                raise ValueError("Request too large.")
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object.")
            if self.path == '/api/receivers/test':
                if installer_status().get('status') in ('queued','installing'):
                    raise RuntimeError('Wait for the update to finish before testing a receiver.')
                index=str(data.get('device','0'))
                if not index.isascii() or not index.isdigit() or len(index)>2:
                    raise ValueError('Choose a receiver index from 0 to 99.')
                return self.reply(200,self.server.workbench.test_receiver(int(index)))
            if self.path == '/api/quit' and os.environ.get('SIGNALPIER_PORTABLE'):
                if installer_status().get('status') in ('queued','installing'):
                    raise RuntimeError('Wait for the update to finish.')
                self.reply(200, {'ok':True})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                return
            if self.path == '/api/usb/setup' and os.environ.get('SIGNALPIER_PORTABLE'):
                if self.server.workbench.busy():
                    raise RuntimeError('Stop the capture first.')
                if not shutil.which('pkexec'):
                    raise ValueError('This desktop has no administrator prompt. See the receiver setup guide.')
                result=subprocess.run(['pkexec','/bin/sh','-c','install -m 644 "$1" /etc/udev/rules.d/60-signalpier-rtlsdr.rules && udevadm control --reload-rules','signalpier-usb',str(Path(__file__).parent/'rtl-sdr.rules')],capture_output=True,text=True,timeout=120)
                if result.returncode:
                    raise ValueError('USB setup was canceled or failed. You can continue using the app.')
            elif self.path == "/api/start":
                if installer_status().get('status') in ('queued','installing'):
                    raise RuntimeError('Wait for the update to finish before starting a capture.')
                self.server.workbench.start(data)
            elif self.path == "/api/stop":
                self.server.workbench.stop()
            elif self.path == "/api/update/install":
                if self.server.workbench.busy():
                    raise RuntimeError('Finish or stop the receiver capture before installing an update.')
                if not self.server.updates.check().get('available'):
                    raise ValueError('No newer update is currently available.')
                request_install()
            else:
                return self.reply(404, {"error": "Not found"})
            self.reply(200, {"ok": True})
        except subprocess.TimeoutExpired:
            self.reply(408, {'error':'The administrator prompt timed out. Try again when ready.'})
        except RuntimeError as exc:
            self.reply(409, {"error": str(exc)})
        except (ValueError, TypeError) as exc:
            self.reply(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = Server(("127.0.0.1", args.port))
    print(f"SignalPier: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.workbench.stop()
        if server.workbench.worker:
            server.workbench.worker.join(timeout=7)
        server.server_close()


if __name__ == "__main__":
    main()
