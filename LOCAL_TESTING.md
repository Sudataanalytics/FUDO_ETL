# Pruebas locales y profiling

El ETL corre contra la **API real de Fudo** pero escribe en un **Postgres local** (Docker).
La base de producción nunca se toca: `docker-compose.yml` fuerza `DB_CONNECTION_STRING` a la base local,
sin importar lo que tenga `.env`. El contenedor usa la misma imagen y el mismo límite de memoria que Cloud Run.

Requisito: Docker Desktop corriendo. Todos los comandos se ejecutan desde la raíz del repo.

En **Git Bash** ejecutar antes `export MSYS_NO_PATHCONV=1`; si no, Git Bash convierte rutas como
`/tools/...` a rutas de Windows y los comandos `docker compose exec/run` fallan. En PowerShell no hace falta.

## 1. Configuración (una sola vez)

```bash
cp .env.example .env
```

Editar `.env`: `CLIENT_NAME` y, si corresponde, `ETL_MEM_LIMIT` / `ETL_CPUS` (meso usa `4g` / `2` en Cloud Run).

## 2. Preparar la base local

```bash
docker compose up -d db
```

Crear tablas y sucursales, dejando activas solo las que se quieren probar (ej. una sola de meso):

```bash
docker compose exec db sh /tools/local_db_setup.sh meso meso_unidad
```

## 3. Token de Fudo

Dos opciones:

**A. Reusar el token de prod (recomendado, no pide tokens nuevos a Fudo).**
En prod (solo lectura):

```sql
SELECT id_sucursal, access_token, token_expiration_utc
FROM public.etl_fudo_tokens WHERE id_sucursal = 'meso_unidad';
```

En la base local (`docker compose exec db psql -U etl -d fudo_local`):

```sql
INSERT INTO public.etl_fudo_tokens (id_sucursal, access_token, token_expiration_utc)
VALUES ('meso_unidad', '<token>', '<expiracion>')
ON CONFLICT (id_sucursal) DO UPDATE
SET access_token = EXCLUDED.access_token, token_expiration_utc = EXCLUDED.token_expiration_utc;
```

Si el token vence (o le quedan menos de `FUDO_TOKEN_MIN_VALIDITY_MINUTES`, 60 por defecto), el ETL intenta pedir uno nuevo.
Sin API keys en `.env` esa sucursal se omite (log `[CREDENCIALES]`) en vez de emitir un token nuevo: es intencional.
Si una corrida larga supera la vigencia del token, aparecerán errores 401 al final.

**B. API keys en `.env`** (`FUDO_<CLIENTE>_<SUCURSAL>_APIKEY/APISECRET`). Pide un token nuevo con las mismas
credenciales que prod; correrlo fuera del horario del Cloud Scheduler.

## 4. Correr y medir

| Comando | Qué deja en `profiling/` |
|---|---|
| `docker compose run --rm --build etl` | `run_*_resumen.txt`: exit code, duración y memoria pico del contenedor (sin overhead de profiler) |
| `docker compose --profile profile run --rm --build etl-memray` | `memray_*_flamegraph.html` (qué código ocupa la memoria en el pico) + `memray_*_stats.txt` |
| `docker compose --profile profile run --rm --build etl-pyspy` | `pyspy_*.svg`: flamegraph de tiempo, incluyendo esperas de red/DB (`--idle`) |

Mientras corre, en otra terminal: `docker stats` muestra RAM/CPU en vivo contra el límite.

La memoria pico del resumen sale del cgroup del contenedor: es la misma métrica que usa Cloud Run para el OOM.
memray y py-spy agregan overhead; para comparar duración y memoria usar el servicio `etl`.

## 5. Comparar `main` contra `develop`

Crear un worktree de `main` fuera del repo y construir la imagen desde ahí con `ETL_SRC`:

```bash
git worktree add ../FUDO_ETL-worktrees/main main
```

```bash
docker compose down -v && docker compose up -d db && docker compose exec db sh /tools/local_db_setup.sh meso meso_unidad
```

```bash
ETL_SRC=../FUDO_ETL-worktrees/main docker compose run --rm --build etl
```

Repetir el reset de la base (y volver a sembrar el token) y correr `docker compose run --rm --build etl` para `develop`.
Comparar los `run_*_resumen.txt`. Ambas corridas deben empezar con la base vacía para que sean equivalentes.

## Reset

```bash
docker compose down -v
```

Borra la base local (incluido el token sembrado).
