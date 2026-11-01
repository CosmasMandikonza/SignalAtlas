"""Read-only PostgreSQL stats; replication is N/A unless observed."""
from __future__ import annotations
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class DatabaseMetrics:
    available: bool
    active_connections: int | None = None
    idle_connections: int | None = None
    database_bytes: int | None = None
    transactions: int | None = None
    replication_lag_bytes: int | None = None
    error: str | None = None
    observed_at: float | None = None


def collect(dsn: str) -> DatabaseMetrics:
    """No SQL writes; only statistics SELECTs from a restricted role."""
    if not dsn:
        return DatabaseMetrics(False, error="No monitoring DSN configured")
    try:
        import psycopg
        with psycopg.connect(dsn, connect_timeout=3, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("""
                    SELECT count(*) FILTER (WHERE state = 'active'),
                           count(*) FILTER (WHERE state = 'idle')
                    FROM pg_stat_activity WHERE datname = current_database()
                """)
                active, idle = cur.fetchone()
                cur.execute("""
                    SELECT pg_database_size(current_database()),
                           xact_commit + xact_rollback
                    FROM pg_stat_database WHERE datname=current_database()
                """)
                size, transactions = cur.fetchone()
                # No replica is configured in the baseline. Do not invent lag.
                return DatabaseMetrics(True, int(active), int(idle), int(size),
                                       int(transactions), observed_at=time.time())
    except Exception as exc:
        # Never expose credentials or DSN in errors.
        return DatabaseMetrics(False, error=f"{type(exc).__name__}: database not reachable",
                               observed_at=time.time())
