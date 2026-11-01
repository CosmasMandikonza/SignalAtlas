from signalatlas.sparkplug import (
    DT_BOOLEAN,
    DT_DOUBLE,
    DT_INT64,
    DT_STRING,
    Payload,
    decode,
    encode,
    topic,
)
import pytest


def test_binary_protobuf_wire_roundtrip():
    raw = encode({"bdSeq": 9, "cpu_pct": 40.5, "Node Control/Rebirth": False,
                  "site_id": "edge-a"}, timestamp_ms=123456, seq=0)
    assert not raw.startswith(b"{")
    p = Payload()
    p.ParseFromString(raw)
    assert p.metrics[0].datatype == DT_INT64
    assert p.metrics[1].datatype == DT_DOUBLE
    assert p.metrics[2].datatype == DT_BOOLEAN
    assert p.metrics[3].datatype == DT_STRING
    obj = decode(raw)
    assert obj.metrics["bdSeq"] == 9
    assert obj.metrics["Node Control/Rebirth"] is False
    assert obj.seq == 0


@pytest.mark.parametrize("bad", [b"", b"a" * 512001])
def test_invalid_payload_rejected(bad):
    with pytest.raises(ValueError):
        decode(bad)


def test_topic_no_wildcards_or_control():
    assert topic("SignalAtlas", "NBIRTH", "edge-a") == "spBv1.0/SignalAtlas/NBIRTH/edge-a"
    with pytest.raises(ValueError):
        topic("a/#", "NBIRTH", "edge-a")
    with pytest.raises(ValueError):
        topic("a", "NCMD_WRONG", "edge-a")


def test_sequence_validated():
    with pytest.raises(ValueError):
        encode({}, 10, seq=256)
    with pytest.raises(TypeError):
        encode({"bad": [1, 2]}, 10)
