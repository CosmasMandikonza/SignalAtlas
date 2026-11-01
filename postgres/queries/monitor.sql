-- Read only, run as monitor. NULL values from restricted stats are not forged.
SELECT state, count(*) FROM pg_stat_activity
 WHERE datname = current_database() GROUP BY state;
SELECT datname, xact_commit, xact_rollback FROM pg_stat_database
 WHERE datname = current_database();
SELECT pg_database_size(current_database()) AS database_size_bytes;
SELECT count(*) AS seed_observations FROM public.synthetic_sensor_observations;
