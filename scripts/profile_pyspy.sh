#!/bin/sh
# Perfil de tiempo con py-spy. --idle incluye el tiempo esperando red/DB/sleep,
# que es donde este ETL pasa la mayor parte del tiempo.
. /tools/_common.sh
install_dev_tools || exit 1
run_id=$(ts)
start=$(date +%s)
# Se lanza el ETL aparte y py-spy se engancha al PID, así se conserva el exit code real del ETL
python fudo_etl/main.py &
etl_pid=$!
py-spy record --idle --rate "${PYSPY_RATE:-20}" --pid "$etl_pid" --output "/out/pyspy_${run_id}.svg"
wait "$etl_pid"
rc=$?
report "$rc" $(( $(date +%s) - start )) "/out/pyspy_${run_id}_resumen.txt"
echo "Abrí profiling/pyspy_${run_id}.svg en el navegador."
exit "$rc"
