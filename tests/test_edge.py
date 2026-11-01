from signalatlas.edge import next_bdseq, synthetic_metrics
import pytest


def test_session_sequence_persistence(tmp_path):
    p = tmp_path / "session" / "a.bdseq"
    assert next_bdseq(p) == 0
    assert next_bdseq(p) == 1
    p.write_text("255")
    assert next_bdseq(p) == 0


def test_invalid_persisted_counter_fails_closed(tmp_path):
    p = tmp_path / "bdseq"
    p.write_text("999")
    with pytest.raises(ValueError):
        next_bdseq(p)


def test_metrics_are_explicitly_synthetic():
    import time
    m = synthetic_metrics("edge-a", time.monotonic() - 5, 1, high_cpu=True)
    assert m["cpu_pct"] == 96.0
    assert m["tag_quality"] == "GOOD"
    assert "device_temperature_c_simulated" in m
    assert "scan_cycle_ms_simulated" in m
