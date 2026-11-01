# Architecture and measurement provenance

## Decisions

1. **Mosquitto instead of MQTT Distributor.** Local Docker without vendor licensing;
   supports auth, ACL and MQTT Will. A real Cirrus Link deployment is a separate gate.
2. **Protobuf subset, not JSON disguised as Sparkplug.** The encoder uses Eclipse
   Tahu's wire field numbers for scalar metrics. Device messages, templates, datasets,
   full aliases and conformance certification are outside the current implementation.
3. **Operational graph is a projection of observations, not the source of truth.**
   The observer tracks reception events; NO actuator commands are published.
4. **Prometheus for numeric trends, browser/Perspective for topology and evidence.**
   Perspective is an intended replacement for the provisional browser, not shipped.

## Evidence and fault semantics

| Observation | State | Reason |
|---|---|---|
| No birth ever received | UNKNOWN | No evidence to claim availability |
| Valid birth/data within 12 sec, good quality, CPU below 90% | HEALTHY | Fresh observed MQTT Sparkplug event |
| Quality not GOOD or reported CPU at least 90% | DEGRADED | Reported bad quality or high CPU |
| Last received event at least 12 sec ago | STALE | Freshness threshold expired |
| Matching `NDEATH` or last event at least 35 sec old | OFFLINE | Session ended or data disappeared |
| Successful birth after death/timeout | Derived HEALTHY/DEGRADED | New observed session |
| Broker subscriber disconnects | Broker OFFLINE; edge→broker links OFFLINE | Direct observer socket failure |
| Ignition not instrumented | UNKNOWN | Never infer a Gateway is healthy |
| Historian SELECT succeeds/fails | PostgreSQL HEALTHY/OFFLINE | Actual read-only query result |

**Subtleties:** Delivery is at-most-once (QoS 0 for node publications), so this
starter does not prove guaranteed observation of every event. A late death from a
previous `bdSeq` is ignored. Duplicate birth is rejected, as are invalid node IDs,
invalid protobuf payloads, skipped sequence numbers and older NDATA timestamps.
The initial `last_healthy` means the most recent **observed healthy message**, not
an indefinitely advancing time. CPU/memory are process/container signals.

## Receiver and network trust boundaries

- Real MQTT socket connectivity is measured. Per-link latency is `null` because
  none has been measured, not an invented value from a publisher timestamp.
- All publisher timestamps are untrusted as wall-clock truth. They support
  within-session out-of-order checks only.
- `/ready` requires MQTT SUBACKs before first edge startup. After broker
  restart, the observer may miss births due to reconnect ordering. Automatic
  session resynchronization is an open acceptance gate. Use `docker compose
  restart edge-a edge-b edge-c` after observer readiness as a known lab recovery.
- Historians and edge nodes are *not* established as direct logical connections;
  the Ignition→PostgreSQL link deliberately remains unknown until JDBC evidence.
- The incident history is bounded in RAM (last 200 transitions). Container
  restart loses previous observations, despite edge `bdSeq` persisting.

## Development lifecycle

CI validates static/unit logic and Compose parsing; Docker/real broker flow must
be exercised in an additional integration environment before release claims.
Evidence artifacts should include raw HTTP JSON responses, container logs,
Prometheus query output, session birth/death messages, and a recording of actual
state transitions with a host-clock stopwatch. Never synthesize those artifacts.
