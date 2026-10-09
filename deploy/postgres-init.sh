#!/bin/bash
# First start only: create the application role (not a superuser) and its own database.
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -v pw="$VIP_DB_PASSWORD" <<-'SQL'
	CREATE ROLE vip_app LOGIN PASSWORD :'pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
	CREATE DATABASE vip OWNER vip_app;
	REVOKE ALL ON DATABASE vip FROM PUBLIC;
SQL
