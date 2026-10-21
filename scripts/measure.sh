#!/bin/sh
# Corre el ETL sin profiler y deja un resumen con duración y memoria pico en /out.
. /tools/_common.sh
run_id=$(ts)
start=$(date +%s)
python fudo_etl/main.py
rc=$?
report "$rc" $(( $(date +%s) - start )) "/out/run_${run_id}_resumen.txt"
exit "$rc"
