from signalatlas.model import Topology
from signalatlas.sparkplug import Decoded


class FakeClock:
    def __init__(self):
        self.t = 1700000000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def payload(seq, bdseq=None, quality="GOOD", cpu=10.0, stamp=1000):
    metrics = {"tag_quality": quality, "cpu_pct": cpu}
    if bdseq is not None:
        metrics["bdSeq"] = bdseq
    return Decoded(stamp, seq, metrics)


def status(g, n="edge-a"):
    return next(x for x in g.snapshot()["nodes"] if x["id"] == n)["status"]


def test_initial_unknown_no_invented_signals():
    g = Topology()
    assert status(g) == "UNKNOWN"
    assert next(n for n in g.snapshot()["nodes"] if n["id"] == "ignition")["status"] == "UNKNOWN"
    assert all(l["status"] == "UNKNOWN" for l in g.snapshot()["links"])


def test_birth_degraded_stale_offline_rebirth():
    c = FakeClock()
    g = Topology(stale_after=10, offline_after=20, clock=c)
    g.broker(True)
    assert g.ingest("NBIRTH", "edge-a", payload(0, 7))
    assert status(g) == "HEALTHY"
    first_healthy = g.nodes["edge-a"].last_healthy
    c.advance(3)
    assert g.ingest("NDATA", "edge-a", payload(1, quality="BAD", stamp=1001))
    assert status(g) == "DEGRADED"
    c.advance(11)
    assert status(g) == "STALE"
    assert g.nodes["edge-a"].last_healthy == first_healthy
    c.advance(10)
    assert status(g) == "OFFLINE"
    assert not g.ingest("NDATA", "edge-a", payload(2, stamp=1002))
    assert g.ingest("NBIRTH", "edge-a", payload(0, 8, stamp=1003))
    assert status(g) == "HEALTHY"


def test_matching_death_then_rebirth():
    c = FakeClock()
    g = Topology(clock=c)
    assert g.ingest("NBIRTH", "edge-a", payload(0, 20))
    assert not g.ingest("NDEATH", "edge-a", Decoded(1500, None, {"bdSeq": 19}))
    assert status(g) == "HEALTHY"
    assert g.ingest("NDEATH", "edge-a", Decoded(1500, None, {"bdSeq": 20}))
    assert status(g) == "OFFLINE"
    assert g.ingest("NBIRTH", "edge-a", payload(0, 21))
    assert status(g) == "HEALTHY"
    assert not g.ingest("NDEATH", "edge-a", Decoded(1500, None, {"bdSeq": 20}))


def test_duplicate_out_of_order_and_sequence_wrap():
    g = Topology(clock=FakeClock())
    assert g.ingest("NBIRTH", "edge-a", payload(0, 0))
    assert not g.ingest("NBIRTH", "edge-a", payload(0, 0))
    assert not g.ingest("NDATA", "edge-a", payload(2, stamp=2000))
    assert g.ingest("NDATA", "edge-a", payload(1, stamp=2000))
    assert not g.ingest("NDATA", "edge-a", payload(2, stamp=1999))
    assert g.ingest("NDATA", "edge-a", payload(2, stamp=2001))
    g.nodes["edge-a"].seq = 255
    assert g.ingest("NDATA", "edge-a", payload(0, stamp=2002))
    assert g.nodes["edge-a"].seq == 0


def test_cpu_threshold_and_unknown_node():
    g = Topology(clock=FakeClock())
    assert not g.ingest("NBIRTH", "not-in-registry", payload(0, 1))
    assert g.ingest("NBIRTH", "edge-a", payload(0, 1, cpu=93))
    assert status(g) == "DEGRADED"


def test_broker_loss_broken_link():
    g = Topology(clock=FakeClock())
    g.broker(True)
    g.ingest("NBIRTH", "edge-a", payload(0, 0))
    assert next(l for l in g.snapshot()["links"] if l["id"] == "edge-a-broker")["status"] == "HEALTHY"
    g.broker(False)
    assert next(l for l in g.snapshot()["links"] if l["id"] == "edge-a-broker")["status"] == "OFFLINE"


def test_incidents_are_only_transitions():
    g = Topology(clock=FakeClock())
    g.ingest("NBIRTH", "edge-a", payload(0, 0))
    count = len(g.incidents)
    g.snapshot()
    g.snapshot()
    assert len(g.incidents) == count


def test_received_rate_window():
    c = FakeClock()
    g = Topology(clock=c)
    g.ingest("NBIRTH", "edge-a", payload(0, 0))
    assert g.snapshot()["nodes"][0]["messages_last_60s"] == 1
    c.advance(61)
    assert g.snapshot()["nodes"][0]["messages_last_60s"] == 0


def test_database_probe_never_fabricates_replication_or_jdbc_link():
    g = Topology(clock=FakeClock())
    assert status(g, "postgres") == "UNKNOWN"
    g.observe_database({"available": True, "observed_at": 1700000000.0,
                        "active_connections": 1, "idle_connections": 0,
                        "replication_lag_bytes": None, "error": None})
    db = next(n for n in g.snapshot()["nodes"] if n["id"] == "postgres")
    assert db["status"] == "HEALTHY"
    assert "replication_lag_bytes" not in db["metrics"]
    assert next(l for l in g.snapshot()["links"] if l["id"] == "ignition-postgres")["status"] == "UNKNOWN"
    g.observe_database({"available": False, "observed_at": 1700000001.0,
                        "error": "OperationalError: database not reachable"})
    assert status(g, "postgres") == "OFFLINE"


def test_bad_cpu_rejected_instead_of_crashing():
    from math import nan
    g = Topology(clock=FakeClock())
    assert not g.ingest("NBIRTH", "edge-a", payload(0, 1, cpu=nan))
    assert not g.ingest("NBIRTH", "edge-a", payload(0, 1, cpu=120))
    assert status(g) == "UNKNOWN"
