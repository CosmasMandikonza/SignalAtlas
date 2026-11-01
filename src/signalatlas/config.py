"""Configuration validation; values never embedded in source control."""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    mqtt_host: str = "broker"
    mqtt_port: int = 1883
    mqtt_user: str = "monitor"
    mqtt_password: str = ""
    mqtt_group: str = "SignalAtlas"
    stale_after: float = 12.0
    offline_after: float = 35.0
    db_dsn: str = ""

    def validate(self) -> None:
        if self.stale_after <= 0 or self.offline_after <= self.stale_after:
            raise ValueError("Require 0 < STALE_AFTER < OFFLINE_AFTER")
        if not self.mqtt_password:
            raise ValueError("MQTT_PASSWORD is required")
        if not self.mqtt_host:
            raise ValueError("MQTT_HOST is required")


def from_env() -> Settings:
    s = Settings(
        mqtt_host=os.environ.get("MQTT_HOST", "broker"),
        mqtt_port=int(os.environ.get("MQTT_PORT", "1883")),
        mqtt_user=os.environ.get("MQTT_USER", "monitor"),
        mqtt_password=os.environ.get("MQTT_PASSWORD", ""),
        stale_after=float(os.environ.get("STALE_AFTER", "12")),
        offline_after=float(os.environ.get("OFFLINE_AFTER", "35")),
        db_dsn=os.environ.get("PG_MONITOR_DSN", ""),
    )
    s.validate()
    return s
