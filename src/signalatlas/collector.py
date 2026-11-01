"""Observational MQTT subscriber. It never publishes MQTT commands."""
from __future__ import annotations
import logging
from prometheus_client import Counter
from .config import Settings
from .model import Topology
from .sparkplug import decode

LOG = logging.getLogger(__name__)
EVENTS = Counter("signalatlas_sparkplug_events_total", "Validated Sparkplug events", ["type", "node"])
REJECTED = Counter("signalatlas_rejected_events_total", "Rejected events", ["reason"])


def process_message(topology: Topology, topic_name: str, blob: bytes,
                    group: str = "SignalAtlas") -> bool:
    parts = topic_name.split("/")
    if len(parts) != 4 or parts[:2] != ["spBv1.0", group]:
        REJECTED.labels("topic").inc()
        return False
    kind, node = parts[2:]
    if kind not in {"NBIRTH", "NDATA", "NDEATH"} or node not in topology.IDS:
        REJECTED.labels("unknown_kind_or_node").inc()
        return False
    try:
        decoded = decode(blob)
    except Exception:
        REJECTED.labels("payload").inc()
        LOG.warning("Rejected invalid Sparkplug payload: %s", topic_name)
        return False
    accepted = topology.ingest(kind, node, decoded)
    if accepted:
        EVENTS.labels(kind, node).inc()
    else:
        REJECTED.labels("state_transition").inc()
    return accepted


def make_subscriber(topology: Topology, settings: Settings):
    import paho.mqtt.client as mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id="signalatlas-observer", protocol=mqtt.MQTTv311)
    client.username_pw_set(settings.mqtt_user, settings.mqtt_password)

    acks = set()

    def on_connect(c, _user, _flags, reason_code, _properties):
        connected = reason_code == 0
        topology.broker(connected)
        acks.clear()
        if connected:
            for kind in ("NBIRTH", "NDATA", "NDEATH"):
                c.subscribe(f"spBv1.0/{settings.mqtt_group}/{kind}/+", qos=0)
            LOG.info("Connected to broker; subscribed to Sparkplug observations")
        else:
            LOG.error("MQTT observer rejected: %s", reason_code)

    def on_disconnect(_c, _u, _flags, _reason_code, _properties):
        topology.broker(False)
        LOG.warning("MQTT observer disconnected")

    def on_subscribe(_c, _u, mid, reason_codes, _properties):
        if any(getattr(reason, "is_failure", False) for reason in reason_codes):
            LOG.error("MQTT subscription denied by broker ACL")
            return
        acks.add(mid)
        if len(acks) >= 3:
            topology.subscription_ready = True

    def on_message(_c, _u, msg):
        process_message(topology, msg.topic, msg.payload, settings.mqtt_group)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    return client
