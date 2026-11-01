"""Prometheus metrics populated solely from observed topology, never demo constants."""
from prometheus_client import Gauge

NODE_PRESENT = Gauge("signalatlas_node_state", "Observed state: 1=active", ["node", "state"])
NODE_MESSAGES = Gauge("signalatlas_node_messages_total", "Messages accepted by receiver", ["node"])
NODE_RATE = Gauge("signalatlas_node_messages_last_60s", "Observed last 60s", ["node"])
DB_AVAILABLE = Gauge("signalatlas_postgres_available", "Read-only query availability")
DB_CONNECTIONS = Gauge("signalatlas_postgres_connections", "Real PostgreSQL connections", ["state"])
BROKER_CONNECTED = Gauge("signalatlas_broker_connected", "MQTT observer socket connected")


def update(topology) -> None:
    snapshot = topology.snapshot()
    for node in snapshot["nodes"]:
        if node["id"].startswith("edge-"):
            for state in ("HEALTHY", "DEGRADED", "STALE", "OFFLINE", "UNKNOWN"):
                NODE_PRESENT.labels(node["id"], state).set(int(state == node["status"]))
            NODE_MESSAGES.labels(node["id"]).set(node["message_count"])
            NODE_RATE.labels(node["id"]).set(node["messages_last_60s"])
    if topology.broker_seen is not None:
        BROKER_CONNECTED.set(int(topology.broker_connected))
    db = topology.database_observation
    if db is not None:
        DB_AVAILABLE.set(int(db["available"]))
        if db["available"]:
            DB_CONNECTIONS.labels("active").set(db["active_connections"])
            DB_CONNECTIONS.labels("idle").set(db["idle_connections"])
