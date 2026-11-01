"""Evidence-grounded topology state machine; no inferred 'green' state."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque
from enum import Enum
import threading
import time
import math
from typing import Any, Callable
from .sparkplug import Decoded

class Status(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


@dataclass
class Node:
    id: str
    status: Status = Status.UNKNOWN
    reason: str = "No observation received"
    last_seen: float | None = None
    last_healthy: float | None = None
    updated_at: float | None = None
    bdseq: int | None = None
    seq: int | None = None
    source_timestamp_ms: int | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    births: int = 0
    deaths: int = 0
    messages: int = 0
    recent_receipts: deque[float] = field(default_factory=deque)


def iso(value: float | None) -> str | None:
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


class Topology:
    """All time comparisons use receiver clock; publisher clocks are untrusted."""
    IDS = ("edge-a", "edge-b", "edge-c")

    def __init__(self, stale_after: float = 12, offline_after: float = 35,
                 clock: Callable[[], float] = time.time):
        if not 0 < stale_after < offline_after:
            raise ValueError("Invalid health thresholds")
        self.clock = clock
        self.stale_after = stale_after
        self.offline_after = offline_after
        self.nodes = {node: Node(id=node) for node in self.IDS}
        self.subscription_ready = False
        self.broker_connected = False
        self.broker_seen: float | None = None
        self.database_observation: dict[str, Any] | None = None
        self.incidents: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def _incident(self, component: str, old: Status, new: Status, reason: str,
                  when: float) -> None:
        if old == new:
            return
        self.incidents.insert(0, {"component": component, "from": old.value,
                                  "to": new.value, "reason": reason,
                                  "observed_at": iso(when)})
        self.incidents = self.incidents[:200]

    def broker(self, connected: bool) -> None:
        with self._lock:
            when = self.clock()
            old = Status.HEALTHY if self.broker_connected else (
                Status.OFFLINE if self.broker_seen is not None else Status.UNKNOWN)
            self.broker_connected = connected
            self.subscription_ready = False
            self.broker_seen = when
            new = Status.HEALTHY if connected else Status.OFFLINE
            self._incident("broker", old, new, "MQTT observer connection changed", when)

    def ingest(self, kind: str, node_id: str, event: Decoded) -> bool:
        if node_id not in self.nodes or kind not in {"NBIRTH", "NDATA", "NDEATH"}:
            return False
        with self._lock:
            node = self.nodes[node_id]
            now = self.clock()
            if kind in {"NBIRTH", "NDATA"}:
                cpu = event.metrics.get("cpu_pct", node.metrics.get("cpu_pct"))
                if cpu is not None and (type(cpu) not in (int, float) or
                                        not math.isfinite(float(cpu)) or not 0 <= cpu <= 100):
                    return False
            if kind == "NBIRTH":
                bdseq = event.metrics.get("bdSeq")
                if event.seq != 0 or type(bdseq) is not int or not 0 <= bdseq <= 255:
                    return False
                if node.bdseq == bdseq and node.status not in {Status.OFFLINE, Status.UNKNOWN}:
                    # Duplicate birth must not reset freshness or counter.
                    return False
                node.bdseq, node.seq = bdseq, 0
                node.status = Status.UNKNOWN  # Rebirth restores an OFFLINE session.
                node.metrics = dict(event.metrics)
                node.births += 1
            elif kind == "NDATA":
                if node.bdseq is None or node.status == Status.OFFLINE:
                    return False
                if event.seq is None or node.seq is None:
                    return False
                if event.seq != (node.seq + 1) % 256:
                    return False
                if (node.source_timestamp_ms is not None and
                        event.timestamp_ms < node.source_timestamp_ms):
                    return False
                if "bdSeq" in event.metrics:
                    return False
                node.metrics.update(event.metrics)
                node.seq = event.seq
            else:
                if (type(event.metrics.get("bdSeq")) is not int or
                        node.bdseq != event.metrics["bdSeq"]):
                    return False  # Ignore late death for an older session.
                prior = node.status
                node.status = Status.OFFLINE
                node.reason = "Observed matching Sparkplug NDEATH"
                node.updated_at = now
                node.deaths += 1
                node.messages += 1
                node.recent_receipts.append(now)
                self._incident(node_id, prior, node.status, node.reason, now)
                return True
            node.source_timestamp_ms = event.timestamp_ms
            node.last_seen = now
            node.messages += 1
            node.recent_receipts.append(now)
            self._refresh(node, now)
            return True

    def _refresh(self, node: Node, now: float) -> None:
        old = node.status
        if node.last_seen is None:
            status, reason = Status.UNKNOWN, "No Sparkplug observation"
        elif node.status == Status.OFFLINE:
            return  # An NDEATH is authoritative until a new NBIRTH.
        elif now - node.last_seen >= self.offline_after:
            status, reason = Status.OFFLINE, "No telemetry before offline timeout"
        elif now - node.last_seen >= self.stale_after:
            status, reason = Status.STALE, "Telemetry exceeded freshness threshold"
        elif "cpu_pct" not in node.metrics:
            status, reason = Status.DEGRADED, "CPU measurement missing"
        elif node.metrics.get("tag_quality") != "GOOD":
            status, reason = Status.DEGRADED, "Reported tag_quality not GOOD"
        elif float(node.metrics.get("cpu_pct", 0)) >= 90:
            status, reason = Status.DEGRADED, "Observed CPU >= 90%"
        else:
            status, reason = Status.HEALTHY, "Fresh Sparkplug observation"
        node.status, node.reason = status, reason
        if status == Status.HEALTHY:
            node.last_healthy = node.last_seen
        if old != status or node.updated_at is None:
            node.updated_at = now
        self._incident(node.id, old, status, reason, now)

    def observe_database(self, observation: dict[str, Any]) -> None:
        with self._lock:
            old = (Status.UNKNOWN if self.database_observation is None else
                   Status.HEALTHY if self.database_observation["available"] else Status.OFFLINE)
            self.database_observation = dict(observation)
            new = Status.HEALTHY if observation["available"] else Status.OFFLINE
            self._incident("postgres", old, new, observation.get("error") or
                           "Observed PostgreSQL SELECT succeeded", self.clock())

    def _serial(self, node: Node) -> dict[str, Any]:
        now = self.clock()
        while node.recent_receipts and now - node.recent_receipts[0] > 60:
            node.recent_receipts.popleft()
        return {"id": node.id, "status": node.status.value, "reason": node.reason,
                "last_seen": iso(node.last_seen), "last_healthy": iso(node.last_healthy),
                "updated_at": iso(node.updated_at), "metrics": dict(node.metrics),
                "birth_events": node.births, "death_events": node.deaths,
                "message_count": node.messages,
                "messages_last_60s": len(node.recent_receipts),
                "source": "MQTT Sparkplug B receiver",
                "latency_ms": None}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = self.clock()
            for node in self.nodes.values():
                self._refresh(node, now)
            broker_status = (Status.HEALTHY if self.broker_connected else
                             Status.OFFLINE if self.broker_seen is not None else Status.UNKNOWN)
            components = [self._serial(n) for n in self.nodes.values()]
            components.append({"id": "broker", "status": broker_status.value,
                               "last_seen": iso(self.broker_seen), "updated_at": iso(self.broker_seen),
                               "last_healthy": None, "source": "MQTT observer socket",
                               "reason": "Observer connected" if self.broker_connected else
                               "Observer disconnected or not started", "metrics": {}, "latency_ms": None})
            components.append({"id": "ignition", "status": Status.UNKNOWN.value,
                               "last_seen": None, "updated_at": None,
                               "last_healthy": None, "source": "No collector configured",
                               "reason": "Not instrumented", "metrics": {}, "latency_ms": None})
            db = self.database_observation
            components.append({"id": "postgres",
                               "status": (Status.HEALTHY if db["available"] else
                                          Status.OFFLINE).value if db else Status.UNKNOWN.value,
                               "last_seen": iso(db["observed_at"]) if db and db["available"] else None,
                               "updated_at": iso(db["observed_at"]) if db else None,
                               "last_healthy": iso(db["observed_at"]) if db and db["available"] else None,
                               "source": "Restricted PostgreSQL SELECTs" if db else "No probe",
                               "reason": ("Read-only stats query succeeded" if db["available"] else
                                          db.get("error")) if db else "No observation",
                               "metrics": {k: v for k, v in db.items() if k not in
                                           {"error", "available", "observed_at"} and v is not None}
                                           if db else {}, "latency_ms": None})
            links = []
            for name in self.IDS:
                node = self.nodes[name]
                status = (Status.UNKNOWN if broker_status == Status.UNKNOWN else
                          Status.OFFLINE if broker_status == Status.OFFLINE else node.status)
                links.append({"id": f"{name}-broker", "from": name, "to": "broker",
                              "status": status.value, "reason": "Broker connection unavailable" if
                              broker_status != Status.HEALTHY else node.reason,
                              "source": "MQTT reception + Sparkplug session", "updated_at": iso(now)})
            links.extend([{"id": "broker-ignition", "from": "broker", "to": "ignition",
                           "status": Status.UNKNOWN.value, "reason": "Ignition not instrumented",
                           "source": "not measured", "updated_at": None},
                          {"id": "ignition-postgres", "from": "ignition", "to": "postgres",
                           "status": Status.UNKNOWN.value, "reason": "JDBC connection not instrumented",
                           "source": "not measured", "updated_at": None}])
            return {"nodes": components, "links": links, "generated_at": iso(now),
                    "incidents": list(self.incidents)}
