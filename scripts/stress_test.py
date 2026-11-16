"""Generate CPU load against the ALB to trigger Auto Scaling.
Requires the app to run with ENABLE_STRESS_ENDPOINT=true (terraform var enable_stress_endpoint).

Usage: python scripts/stress_test.py http://<alb-dns> --threads 40 --duration 600
"""
import argparse
import threading
import time
import urllib.request

counts = {"ok": 0, "err": 0}
lock = threading.Lock()


def worker(url, end):
    while time.time() < end:
        try:
            urllib.request.urlopen(f"{url}/stress?seconds=2", timeout=15).read()
            key = "ok"
        except Exception:
            key = "err"
        with lock:
            counts[key] += 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--threads", type=int, default=40)
    p.add_argument("--duration", type=int, default=600, help="seconds")
    a = p.parse_args()
    end = time.time() + a.duration
    ts = [threading.Thread(target=worker, args=(a.url.rstrip("/"), end)) for _ in range(a.threads)]
    [t.start() for t in ts]
    while time.time() < end:
        time.sleep(10)
        print(f"ok={counts['ok']} err={counts['err']}", flush=True)
    [t.join() for t in ts]
