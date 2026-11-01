"""Three selectable synthetic industrial edge nodes; no actuator or output commands."""
from __future__ import annotations
import argparse
import json
import logging
import math
import os
from pathlib import Path
import signal
import time
import psutil
from .sparkplug import decode, encode, topic

LOG = logging.getLogger("signalatlas.edge")


def next_bdseq(path: Path) -> int:
    """Persist session counter so process restarts don't reuse a Will bdSeq."""
    path.parent.mkdir(parents=True, exist_ok=True)
    old = -1
    if path.exists():
        old = int(path.read_text().strip())
        if not 0 <= old <= 255:
            raise ValueError("Invalid persisted bdSeq")
    value = (old + 1) % 256
    temporary = path.with_suffix(".tmp")
    temporary.write_text(f"{value}\n")
    temporary.replace(path)
    return value


def synthetic_metrics(node: str, started: float, ticks: int,
                      high_cpu: bool = False) -> dict[str, str | float | int]:
    # Industrial temperature and scan duration are explicitly synthetic.
    return {
        "site_id": node,
        "cpu_pct": 96.0 if high_cpu else round(psutil.cpu_percent(interval=None), 2),
        "memory_pct": round(psutil.virtual_memory().percent, 2),
        "uptime_seconds": int(time.monotonic() - started),
        "device_temperature_c_simulated": round(33 + 4 * math.sin(ticks / 10), 2),
        "scan_cycle_ms_simulated": round(8.5 + abs(math.sin(ticks / 7)), 2),
        "tag_quality": "GOOD",
        "message_count": ticks,
        "last_publish_ms": int(time.time() * 1000),
    }


def run(node: str) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install package dependencies: pip install -e .") from exc
    host = os.environ.get("MQTT_HOST", "broker")
    user, password = os.environ.get("MQTT_USER", node), os.environ.get("MQTT_PASSWORD", "")
    if not password:
        raise SystemExit("MQTT_PASSWORD is required")
    group = os.environ.get("MQTT_GROUP", "SignalAtlas")
    interval = float(os.environ.get("PUBLISH_INTERVAL", "3"))
    if interval <= 0:
        raise SystemExit("PUBLISH_INTERVAL must be positive")
    bd_path = Path(os.environ.get("BDSEQ_FILE", f"/state/{node}.bdseq"))
    started = time.monotonic()
    stop = False
    session = {"seq": 0, "bdseq": None, "birth": False}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"signalatlas-{node}",
                         protocol=mqtt.MQTTv311, clean_session=True)
    client.username_pw_set(user, password)

    def publish(kind: str, metrics: dict, seq: int | None) -> None:
        result = client.publish(topic(group, kind, node),
                                encode(metrics, int(time.time() * 1000), seq),
                                qos=0, retain=False)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            LOG.error("%s publication rejected rc=%s", kind, result.rc)

    def birth() -> None:
        session["seq"] = 0
        payload = synthetic_metrics(node, started, 0)
        payload.update({"bdSeq": session["bdseq"], "Node Control/Rebirth": False})
        publish("NBIRTH", payload, 0)
        session["birth"] = True
        LOG.info("NBIRTH node=%s bdSeq=%s", node, session["bdseq"])

    def on_connect(c, _u, _f, reason_code, _p):
        if reason_code != 0:
            LOG.error("MQTT connection rejected: %s", reason_code)
            return
        # bdSeq was persisted and embedded in Will BEFORE CONNECT; reuse it.
        session["birth"] = False
        c.subscribe(topic(group, "NCMD", node), qos=1)
        birth()

    def on_message(_c, _u, msg):
        try:
            packet = decode(msg.payload)
            if packet.metrics.get("Node Control/Rebirth") is True:
                LOG.info("Received non-actuating Sparkplug rebirth request")
                birth()
        except (ValueError, TypeError):
            LOG.warning("Rejected malformed NCMD")

    def on_disconnect(_c, _u, _flags, reason, _p):
        session["birth"] = False
        LOG.warning("Edge MQTT connection lost: %s", reason)

    def handle_signal(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    client.on_connect, client.on_message, client.on_disconnect = (
        on_connect, on_message, on_disconnect)
    # Sparkplug Will is fixed in MQTT CONNECT. Persist the bdSeq before CONNECT;
    # handle reconnect with an explicit new connection loop to replace the Will.
    client.reconnect_delay_set(min_delay=1, max_delay=5)
    ticks = 0
    while not stop:
        session["bdseq"] = next_bdseq(bd_path)
        session["seq"], session["birth"] = 0, False
        client.will_set(topic(group, "NDEATH", node),
                        encode({"bdSeq": session["bdseq"]}, int(time.time()*1000)),
                        qos=1, retain=False)
        # loop_forever with reconnect would reuse a stale Will. Instead run one
        # connection per outer-loop iteration and close/rebuild when disconnected.
        try:
            client.connect(host, int(os.environ.get("MQTT_PORT", "1883")), keepalive=12)
            while not stop:
                rc = client.loop(timeout=1.0)
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    break
                if not session["birth"]:
                    continue
                now = time.monotonic()
                if not hasattr(run, "_next_send") or now >= getattr(run, "_next_send"):
                    ticks += 1
                    session["seq"] = (int(session["seq"]) + 1) % 256
                    publish("NDATA", synthetic_metrics(
                        node, started, ticks, os.environ.get("SIMULATE_HIGH_CPU") == "1"),
                        int(session["seq"]))
                    run._next_send = now + interval
            if stop and session["birth"]:
                publish("NDEATH", {"bdSeq": session["bdseq"]}, None)
                client.loop(timeout=0.3)
                client.disconnect()
        except (OSError, ValueError) as exc:
            LOG.warning("MQTT unavailable node=%s: %s", node, exc)
        if not stop:
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True, choices=("edge-a", "edge-b", "edge-c"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format=json.dumps({"time": "%(asctime)s", "level": "%(levelname)s",
                                           "logger": "%(name)s", "message": "%(message)s"}))
    run(args.node)

if __name__ == "__main__":
    main()
