# Troubleshooting and failure evidence

**No services:** Run `docker compose ps`, then `docker compose logs --tail=100 broker topology-api`.
Check `.env`, Docker daemon, password hash bootstrap, memory and conflicting ports.

**API /health alive but /ready 503:** MQTT not connected or SUBACK not received.
Validate broker logs, the monitor credentials and the three topic-specific ACLs.
Never interpret /health as edge site connectivity.

**Edge unknown while broker healthy:** NBIRTH was not received, possibly due to
observer starting after the edge or reconnect ordering. Verify topology-api ready,
then `docker compose restart edge-a edge-b edge-c` to force fresh births. If
restarts continue to fail, inspect credentials, `/state` volume permissions and
edge logs. Do not set healthy manually.

**Edge becomes stale:** `last_seen` passes STALE_AFTER (default 12 s). Compare
edge timestamps, observer logs and message rates; verify no bogus CPU measurement.

**Edge offline:** Matching NDEATH or an OFFLINE_AFTER timeout. Inspect the
recorded `reason`, incident history and broker socket status to distinguish site
failure from infrastructure failure. NDEATH after kill depends on keepalive.

**PostgreSQL unknown/offline:** Ensure initialization ran on an empty named volume.
Existing volumes do not re-run `/docker-entrypoint-initdb.d`. Do not run
`docker compose down -v` unless you deliberately want to destroy local data.
Run SQL as monitor and verify only SELECT succeeds before trusting permissions.

**Ignition UNKNOWN:** This is expected until the vendor integration is installed,
licensed, configured and live measurement is proven. It is not a telemetry fault.

**Grafana graph empty:** Prometheus must scrape `/metrics` successfully; the
metric counters start only after actual validated observations. Use Prometheus
Targets, then check `signalatlas_sparkplug_events_total`.

**Observations disappear on restart:** Current in-memory topology is intentionally
not durable. Incident/event persistence is a future phase. Do not claim durable
forensic history until it exists.
