#!/bin/sh
# Perfil de memoria con memray: genera el .bin, un flamegraph HTML (pico de memoria) y estadísticas.
. /tools/_common.sh
install_dev_tools || exit 1
run_id=$(ts)
bin="/out/memray_${run_id}.bin"
start=$(date +%s)
python -m memray run --output "$bin" fudo_etl/main.py
rc=$?
dur=$(( $(date +%s) - start ))
python -m memray flamegraph --force --output "/out/memray_${run_id}_flamegraph.html" "$bin"
python -m memray stats "$bin" > "/out/memray_${run_id}_stats.txt"
report "$rc" "$dur" "/out/memray_${run_id}_resumen.txt"
echo "Abrí profiling/memray_${run_id}_flamegraph.html en el navegador."
exit "$rc"
