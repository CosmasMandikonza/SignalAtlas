# Sparkplug B integration contract

Reference: [Eclipse Sparkplug Specification 3.0](https://sparkplug.eclipse.org/specification/version/3.0/documents/sparkplug-specification-3.0.0.pdf)
and [Eclipse Tahu protobuf schema](https://github.com/eclipse-tahu/tahu/blob/master/sparkplug_b/sparkplug_b.proto).

## Current on-wire implementation

Topics: `spBv1.0/SignalAtlas/{NBIRTH|NDATA|NDEATH}/edge-a` and equivalent
for edge-b and edge-c. MQTT 3.1.1 transport. Protobuf with Tahu's scalar field
numbers. Birth includes `seq=0`, `bdSeq` (Int64), `Node Control/Rebirth=false`,
metric definitions and values. Data increments `seq` modulo 256. The MQTT Will
is registered **before CONNECT**, on `NDEATH`, QoS 1 / not retained, with a matching
`bdSeq`. An intentional shutdown sends a non-retained NDEATH before DISCONNECT.
Each reconnect increments persisted `bdSeq`, modulo 256.

Each edge subscribes to its own `NCMD` topic (QoS 1) and accepts only a
metadata-only `Node Control/Rebirth` request; it contains NO equipment actuator
functionality. The monitoring observer itself is never authorized to publish
that request. It can only subscribe to NBIRTH / NDATA / NDEATH.

## What is NOT claimed

This is a deliberately narrow scalar subset; not a full Tahu library, Sparkplug
TCK compliance certificate, MQTT Engine tested integration, device DBIRTH,
DDATA, DDEATH, host STATE awareness, alias negotiation, file/dataset/template
metric support, persistent offline event history, or certified session rebirth
semantics. In particular, the current sequence validator drops gaps rather than
resynchronizing through explicit host coordination. Before claiming a production
Sparkplug implementation, adopt the full Eclipse Tahu generated classes/client,
run conformance tests and verify against a real Ignition MQTT Engine installation.

## Key observable transitions

1. Process starts; Will armed; connects; subscribes to NCMD; publishes NBIRTH.
2. Process publishes binary NDATA at the configured interval.
3. `docker compose stop edge-b`: edge-b emits NDEATH (normally); MQTT observer
   matches session and marks edge-b OFFLINE.
4. Force-kill or unplug: broker emits NDEATH Will after connection failure is
   detected. Detection time is a measured outcome, not a constant promise.
5. Restart: new `bdSeq`/NBIRTH and new in-order NDATA; state is restored.

If the broker is restarted, retry delivery and re-subscription ordering can
cause a lost birth. The tracked integration blocker is documented in
`docs/backlog.md`; do not silently color such nodes green.
