#!/bin/sh
# Local-development roles for the isolated erratascope-w03 Compose project.
# Credentials here are deliberately local-only and never used for hosted access.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'erratascope_migrator') THEN
    CREATE ROLE erratascope_migrator LOGIN PASSWORD 'dev_migrator_password';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'erratascope_app') THEN
    CREATE ROLE erratascope_app LOGIN PASSWORD 'dev_app_password';
  END IF;
END
$$;
GRANT CONNECT ON DATABASE erratascope TO erratascope_migrator, erratascope_app;
CREATE SCHEMA IF NOT EXISTS erratascope AUTHORIZATION erratascope_migrator;
EOSQL

if ! psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'erratascope_test'" | grep -q 1; then
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE erratascope_test OWNER erratascope_migrator"
fi
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname erratascope_test \
  -c "CREATE SCHEMA IF NOT EXISTS erratascope AUTHORIZATION erratascope_migrator"
