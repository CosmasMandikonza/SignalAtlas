# Five-minute live demonstration (procedure — execution not yet certified)

**Prerequisite:** `make up`, `docker compose ps`, and `/ready` shows 200.
Record terminal output with timestamps. Use *live Docker results* only.

- **0:00–0:45:** Open the topology browser at `http://127.0.0.1:8000`.
  Show live edge nodes, observed `last_seen`, `reason`, and explicit UNKNOWN
  Ignition. Confirm broker subscriber readiness and no write actions.
- **0:45–1:30:** View `/api/topology` and `python -m signalatlas.diagnostics`.
  Explain `bdSeq`, binary protobuf and 60-second observed publish counts.
- **1:30–2:15:** Run `docker compose stop edge-b`. Observe the matching
  Sparkplug NDEATH; capture actual host stopwatch elapsed time and OFFLINE
  incident. If no NDEATH arrives, identify the failure instead of editing data.
- **2:15–3:00:** Open Grafana at `http://127.0.0.1:3000` and look for the
  validated event trend drop. Run `docker compose start edge-b`; watch a fresh
  birth and the transition back to a healthy observed state.
- **3:00–3:45:** Inspect `/api/database` and the Postgres metrics. Prove these
  came from a SELECT-only account; query stats availability is *not* proof of
  replication or slow-query metrics. These are not built yet.
- **3:45–5:00:** Explain the ACL restriction on monitor, the uninstrumented
  Ignition limitation and the next independent integration gate. Show the
  pytest output from this machine and source files from the clone.

**Important:** The requested complete demo (real Ignition tags, active slow-query
detection and independent fail/recovery verification) does not yet pass; it
remains a future release gate. Do not record or submit it as completed.
