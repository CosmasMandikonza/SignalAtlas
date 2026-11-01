# Implementation backlog and GitHub issue drafts

This repository has NOT been uploaded to GitHub, so GitHub issues/milestones
have NOT been created. Copy these scoped issue drafts when you create the repo;
then link each PR and evidence to its issue. No unverified work is marked done.

| Gate | GitHub issue title | Acceptance evidence |
|---|---|---|
| P0 | Foundation: reproducible local Compose + CI | Clean clone `make up`, Compose health, GitHub CI green, fixed image tags |
| P1 | Edge: Sparkplug sessions and interoperability | Broker captures, official Tahu interop tests, reconnect/late Will scenarios |
| P2 | MQTT: broker identities + ACL + resynchronization | Auth negative tests, connection counters, birth recovery after broker restart |
| P3 | Topology: REST inventory/causality | No invented health, incident attribution, durable event journal |
| P4 | PostgreSQL: limited monitor + historian | SQL write-denial evidence, live stats and controlled slow-query detector |
| P5 | Ignition: licensed Gateway + MQTT Engine | Compatible module installation and real Sparkplug tags |
| P6 | Perspective: operator connectivity map | Versioned export, bind each node to real evidence, actual screenshots |
| P7 | Grafana: five deep-dive dashboards | Scrape tests, real values, NO fictitious replication latency |
| P8 | Faults: deterministic 9-scenario harness | Time-to-detect and recovery files for each required scenario |
| P9 | Optional AWS: read-only EC2/RDS adapter | Explicit AWS approval, IAM policy audit and real CloudWatch evidence |
| P10 | Tests: integration and failure suites | Docker tests green, Python tests green, timestamps and logs |
| P11 | Security: no control-plane permissions | MQTT ACL deny tests, SQL denied writes, TLS plan |
| P12 | Demo: clean-clone reproducibility | Recorded 5-minute demo, real Ignition, PostgreSQL slow-query alert |

**Gaps in current version:** CI not run on GitHub, Docker runtime not available
in authoring environment, broker restart race, no persistent topology/incidents,
no real sensor tags, no simulator network fault, no replication/slow-query
inspection, no actual Gateway, no Perspective resources, no AWS.

## No-go gates for claims

- Do not claim 'Sparkplug compliant' before official interoperability/TCK.
- Do not claim 'operational SCADA/OT' before real authorized Ignition session.
- Do not claim 'read-only proven' before negative MQTT/SQL integration tests.
- Do not claim 'CI green' until the specific workflow actually passes.
- Do not add a resume bullet asserting AWS/RDS, Ignition or Perspective based on
  documentation or simulated objects alone.
