"""Validate local env and provision development-only broker password hashes."""
from pathlib import Path
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("MQTT_COLLECTOR_PASSWORD", "MQTT_EDGE_A_PASSWORD",
            "MQTT_EDGE_B_PASSWORD", "MQTT_EDGE_C_PASSWORD",
            "POSTGRES_ADMIN_PASSWORD", "POSTGRES_MONITOR_PASSWORD",
            "POSTGRES_WRITER_PASSWORD", "GRAFANA_ADMIN_PASSWORD")


def load():
    file = ROOT / ".env"
    if not file.exists():
        raise SystemExit("Missing .env: copy .env.example and fill secrets")
    env = {}
    for line in file.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit("Malformed .env line")
        key, val = line.split("=", 1)
        env[key.strip()] = val.strip().strip("'\"")
    for key in REQUIRED:
        if len(env.get(key, "")) < 12:
            raise SystemExit(f"{key} is unset or shorter than 12 characters")
    for key in REQUIRED:
        if not re.fullmatch(r"[A-Za-z0-9_-]{12,}", env[key]):
            raise SystemExit(f"{key} must use 12+ letters/digits/_/- only for Compose DSN safety")
    if len(set(env[k] for k in REQUIRED)) != len(REQUIRED):
        raise SystemExit("Use distinct passwords for all identities")
    return env


def main():
    env = load()
    output = ROOT / "runtime/mosquitto"
    output.mkdir(parents=True, exist_ok=True)
    # Development container tool; generated password hashes stay gitignored.
    # The command arguments do not include secrets; env vars are inherited by Docker.
    names = ["MQTT_COLLECTOR_PASSWORD", "MQTT_EDGE_A_PASSWORD",
             "MQTT_EDGE_B_PASSWORD", "MQTT_EDGE_C_PASSWORD"]
    script = "set -eu; mosquitto_passwd -b -c /out/passwords monitor \"$MQTT_COLLECTOR_PASSWORD\""
    for user, key in zip(("edge-a", "edge-b", "edge-c"), names[1:]):
        script += f'; mosquitto_passwd -b /out/passwords {user} "${key}"'
    script += "; chmod 644 /out/passwords"
    docker_env = os.environ.copy()
    docker_env.update(env)
    user = (["--user", f"{os.getuid()}:{os.getgid()}"]
            if hasattr(os, "getuid") else [])
    command = ["docker", "run", "--rm", *user,
               "-v", f"{output}:/out", *(arg for k in names for arg in ("-e", k)),
               "eclipse-mosquitto:2", "sh", "-c", script]
    subprocess.run(command, check=True, env=docker_env)
    print("Broker password hashes provisioned; plaintext values remain in .env")

if __name__ == "__main__":
    main()
