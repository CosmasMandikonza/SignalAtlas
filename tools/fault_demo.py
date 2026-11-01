"""Guided two-scenario reversible smoke demo. Does not pretend to test all faults."""
import subprocess
from urllib.request import urlopen


def check():
    try:
        with urlopen("http://localhost:8000/api/topology", timeout=3) as r:
            print(r.read(400).decode())
    except OSError as exc:
        print("API unavailable:", type(exc).__name__)


def run(*args):
    subprocess.run(["docker", "compose", *args], check=True)


def main():
    print("This demo stops edge-b and then restores it. Monitoring only; no actuators.")
    input("Press Enter to capture the baseline API state...")
    check()
    input("Press Enter to stop edge-b (graceful NDEATH)...")
    try:
        run("stop", "edge-b")
        check()
        input("Inspect /, /api/incidents and Grafana. Press Enter to recover...")
    finally:
        run("start", "edge-b")
    check()
    print("Observe the new birth + healthy transition after a few seconds.")
    print("Other faults (network isolation, broker outage, PostgreSQL outage) are backlog items.")

if __name__ == "__main__":
    main()
