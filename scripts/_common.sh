# Funciones compartidas por los scripts de medición (se usan dentro del contenedor).

ts() { date +%Y%m%d_%H%M%S; }

# Memoria pico del contenedor según el cgroup (lo mismo que mira Cloud Run para el OOM)
container_peak_mb() {
  for f in /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory/memory.max_usage_in_bytes; do
    if [ -r "$f" ]; then
      echo $(( $(cat "$f") / 1024 / 1024 ))
      return
    fi
  done
  echo "n/d"
}

report() {
  # $1 = exit code, $2 = segundos, $3 = archivo de resumen
  {
    echo "exit_code=$1"
    echo "duracion_seg=$2"
    echo "memoria_pico_contenedor_mb=$(container_peak_mb)${PEAK_NOTE:+ ($PEAK_NOTE)}"
    echo "limite_memoria=${ETL_MEM_LIMIT:-2g}"
    echo "cliente=${CLIENT_NAME}"
  } | tee "$3"
}

install_dev_tools() {
  # pip también consume memoria del contenedor: el pico de estas corridas no sirve para comparar
  PEAK_NOTE="incluye pip install; para comparar usar el servicio etl"
  pip install -q --disable-pip-version-check --root-user-action=ignore -r /tools/requirements-dev.txt
}
