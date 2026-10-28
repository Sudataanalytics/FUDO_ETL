#!/bin/sh
# Prepara la base LOCAL: crea tablas base, carga las sucursales del cliente y deja activas
# solo las indicadas. Se ejecuta dentro del contenedor db:
#   docker compose exec db sh /tools/local_db_setup.sh <cliente> [id_branch ...]
set -e
client="$1"
if [ -z "$client" ]; then
  echo "Uso: local_db_setup.sh <cliente> [id_branch ...]" >&2
  exit 1
fi
shift
psql_local() { psql -v ON_ERROR_STOP=1 -q -U etl -d fudo_local "$@"; }

psql_local -f /repo/fudo_etl/sql/base_raw_tables_and_metadata.sql
psql_local -f "/repo/clients/${client}/branches.sql"

if [ "$#" -gt 0 ]; then
  list=""
  for b in "$@"; do list="${list:+$list,}'$b'"; done
  psql_local -c "UPDATE public.config_fudo_branches SET is_active = (id_branch IN (${list}));"
fi
psql_local -c "SELECT id_branch, branch_name, is_active FROM public.config_fudo_branches ORDER BY id_branch;"
