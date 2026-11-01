# Read-only security boundary

This repository contains **no equipment control clients**. Synthetic edge
publishers have no actuator endpoints and cannot modify physical systems.

## Credentials and least privilege

- All 8 environment passwords are supplied locally through `.env`; no defaults
  are committed. `.env` and broker password hashes are gitignored.
- The observer authenticates as `monitor` and Mosquitto's ACL allows **read
  only** on NBIRTH / NDATA / NDEATH. It has no MQTT write permission, including
  NCMD or DCMD.
- Each synthetic edge has a distinct MQTT identity and can publish only its
  own birth/data/death topics; its only subscribed command topic is its own NCMD
  rebirth request, which affects metadata session state, not equipment.
- The `monitor` SQL role has CONNECT, USAGE on public schema, SELECT on the
  synthetic historian table, and normal accessible PostgreSQL statistics.
  It has NO DML/DDL rights on application tables. It is not a superuser,
  `pg_monitor`, or `pg_read_all_stats` member. PostgreSQL grants on stats views
  must be assessed separately before widening the role.
- `synthetic_writer` exists solely to seed or evolve the synthetic fixture.
  It is **not** used in topology-api.
- PostgreSQL is not port-published to the host. Services use an isolated
  Compose network; UI/API and Prometheus/Grafana/MQTT bind to loopback.

## Boundaries and limitations

- Local MQTT is plaintext, with password authentication and ACL, to simplify
  the lab. Do not deploy this configuration across untrusted networks. Upgrade
  to TLS (mTLS where applicable), secure secret storage, hardened container
  runtime and tighter egress/ingress before using real OT/production data.
- Basic auth/SSO isn't configured for the read-only API. Binding to 127.0.0.1
  is an educational-only choice, not production identity management.
- The initial PostgreSQL superuser is used by container initialization, never
  by the metrics reader. The author must demonstrate negative tests for
  INSERT, UPDATE, DELETE, CREATE and DROP before claiming enforced SQL access.
- Broker password hashes are local files readable by the broker process.
  The bootstrap command temporarily passes password values to `mosquitto_passwd`
  in the process argument vector **inside a disposable local container**;
  this is unsuitable for secret-sensitive production environments.
- HTTP metrics and topology state must not leak credentials, database DSNs or
  source IPs. Errors return error types only. No production hostnames are used.
- This is neither penetration-tested nor independently security-audited.
