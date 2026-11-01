"""Operator CLI querying the read-only API, no privileged broker operations."""
import argparse
import json
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description="SignalAtlas MQTT event diagnostics")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/topology")
    args = parser.parse_args()
    with urlopen(args.url, timeout=5) as response:  # noqa: S310 - operator selected URL
        data = json.load(response)
    print(f"{'NODE':<13} {'STATE':<12} {'LAST SEEN':<30} {'BIRTH':>6} {'DEATH':>6} {'COUNT':>6} {'RATE/m':>7}")
    for node in data["nodes"]:
        if not node["id"].startswith("edge-"):
            continue
        print(f"{node['id']:<13} {node['status']:<12} "
              f"{(node['last_seen'] or 'N/A'):<30} {node['birth_events']:>6} "
              f"{node['death_events']:>6} {node['message_count']:>6} {node['messages_last_60s']:>7}")
    print("RATE/m reports observed messages in a moving 60-second window.")

if __name__ == "__main__":
    main()
