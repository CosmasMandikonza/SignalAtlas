from fastapi.testclient import TestClient
from signalatlas.api import create_app
from signalatlas.model import Topology
from signalatlas.sparkplug import encode
from signalatlas.collector import process_message


def test_read_only_routes_and_unmeasured():
    client = TestClient(create_app())
    assert client.get("/health").json() == {"api": "alive", "broker_connected": False}
    data = client.get("/api/topology").json()
    assert len(data["nodes"]) == 6
    assert len(data["links"]) == 5
    assert client.get("/api/nodes/does-not-exist").status_code == 404
    assert client.get("/api/database").json()["replication_lag_bytes"] is None
    assert "signalatlas_sparkplug_events_total" in client.get("/metrics").text
    assert "SignalAtlas" in client.get("/").text
    assert client.post("/api/nodes").status_code == 405


def test_collector_payload_to_api():
    g = Topology()
    client = TestClient(create_app(topology=g))
    assert process_message(g, "spBv1.0/SignalAtlas/NBIRTH/edge-b",
                           encode({"bdSeq": 0, "Node Control/Rebirth": False,
                                   "cpu_pct": 20.0, "tag_quality": "GOOD"}, 1000, 0))
    assert client.get("/api/nodes/edge-b").json()["status"] == "HEALTHY"
    assert not process_message(g, "spBv1.0/SignalAtlas/NBIRTH/hacker",
                               encode({"bdSeq": 0}, 1000, 0))
    assert not process_message(g, "spBv1.0/SignalAtlas/NDATA/edge-b", b"notprotobuf")


def test_invalid_setting_thresholds():
    import pytest
    with pytest.raises(ValueError):
        Topology(stale_after=4, offline_after=4)


def test_ready_requires_subscription_ack():
    graph = Topology()
    client = TestClient(create_app(topology=graph))
    assert client.get("/ready").status_code == 503
    graph.broker(True)
    assert client.get("/ready").status_code == 503
    graph.subscription_ready = True
    assert client.get("/ready").json()["mqtt_subscription"] == "ready"
