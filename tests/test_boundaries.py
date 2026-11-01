from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_monitor_identity_has_no_mqtt_write_grant():
    sections = (ROOT / "infrastructure/docker/mosquitto.acl").read_text().split("user ")
    observer = next(section for section in sections if section.startswith("monitor\n"))
    assert "topic read " in observer
    assert "topic write " not in observer
    assert "NCMD" not in observer
    assert "DCMD" not in observer


def test_monitor_sql_no_dml_grants():
    sql = (ROOT / "postgres/init/00-roles.sh").read_text()
    assert "GRANT SELECT ON public.synthetic_sensor_observations TO monitor;" in sql
    assert "GRANT SELECT, INSERT ON public.synthetic_sensor_observations TO synthetic_writer;" in sql
    assert "GRANT CONNECT ON DATABASE signalatlas TO monitor, synthetic_writer;" in sql


def test_no_public_postgres_network_port():
    import yaml
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    assert "ports" not in compose["services"]["postgres"]
    assert compose["services"]["topology-api"]["ports"] == ["127.0.0.1:8000:8000"]
