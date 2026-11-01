#!/bin/sh
set -eu
# Standard postgres entrypoint runs this during the first initialization only.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v monitor_pw="$POSTGRES_MONITOR_PASSWORD" -v writer_pw="$POSTGRES_WRITER_PASSWORD" <<'SQL'
CREATE ROLE monitor LOGIN PASSWORD :'monitor_pw';
CREATE ROLE synthetic_writer LOGIN PASSWORD :'writer_pw';
REVOKE ALL ON DATABASE signalatlas FROM PUBLIC;
GRANT CONNECT ON DATABASE signalatlas TO monitor, synthetic_writer;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO monitor, synthetic_writer;
CREATE TABLE public.synthetic_sensor_observations (
    observed_at timestamptz NOT NULL,
    site_id text NOT NULL,
    temperature_c double precision NOT NULL,
    PRIMARY KEY (observed_at,site_id)
);
INSERT INTO public.synthetic_sensor_observations
SELECT now() - n * interval '1 minute', 'edge-a', 30 + 2 * sin(n::double precision/6)
FROM generate_series(1,120) AS n;
GRANT SELECT ON public.synthetic_sensor_observations TO monitor;
GRANT SELECT, INSERT ON public.synthetic_sensor_observations TO synthetic_writer;
-- NO write permissions for monitor. No superuser, no pg_monitor umbrella role.
-- pg_read_all_stats can be added only after the scope trade-off is reviewed.
SQL
