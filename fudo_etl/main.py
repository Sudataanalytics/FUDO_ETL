# fudo_etl/main.py
import logging
import json
from datetime import datetime, timedelta, timezone
import uuid
import re
from hashlib import md5
import os
from typing import Callable
import sys         # Importar sys para manejar sys.path
import importlib   # Importar importlib para la importación dinámica
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2

# Tus módulos (importaciones directas/relativas a la raíz del WORKDIR /app en Docker)
from modules.config import load_config
from modules.db_manager import DBManager
from modules.etl_metadata_manager import ETLMetadataManager
from modules.fudo_auth import BranchTokenProvider, FudoAuthenticator, CREDENTIAL_ERRORS
from modules.fudo_api_client import (FudoApiClient, EntityForbiddenError, WINDOW_FIELD, WINDOWED_ENTITIES,
                                     INCLUDED_CHILDREN, format_fudo_date, parse_fudo_date)

# Versión del ETL. Aparece en cada línea de log para identificar qué build corre en GCP.
ETL_VERSION = "V2.0"

# Configuración básica de logging para todo el script principal.
# threadName identifica sucursal/hilo, ya que las entidades se extraen en paralelo.
logging.basicConfig(level=logging.INFO,
                    format=f'##{ETL_VERSION}## %(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ENTITIES_TO_EXTRACT = [
    'customers', 'discounts', 'expenses', 'expense-categories', 'ingredients',
    'items', 'kitchens', 'payments', 'payment-methods', 'product-categories',
    'product-modifiers', 'products', 'roles', 'rooms', 'sales', 'tables', 'users',
    'providers'
]

# Elimina el DROP de las definiciones de MVs para no recrearlas en cada corrida
DROP_MV_PATTERN = re.compile(r"DROP\s+MATERIALIZED\s+VIEW[^;]*;", re.IGNORECASE)

def raw_table_for(entity: str) -> str:
    return f"fudo_raw_{entity.replace('-', '_')}"


def child_entity_for(entity: str) -> str | None:
    """Entidad hija que llega incluida en la respuesta de 'entity' (ej. 'subitems' de 'items'), o None."""
    child = INCLUDED_CHILDREN.get(entity)
    return child['include'] if child else None


# Nueva función para leer el contenido de un archivo SQL
def read_sql_file(relative_path: str) -> str:
    """Lee un archivo SQL desde la raíz del proyecto."""
    # Sube un nivel desde fudo_etl/modules o fudo_etl/main.py hasta la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    absolute_path = os.path.join(base_dir, relative_path)
    with open(absolute_path, 'r', encoding='utf-8') as f:
        return f.read()


def prepare_records(page: list[dict], id_sucursal: str,
                    window_ts: Callable[[dict], datetime | None] | None = None) -> list[dict]:
    """
    Convierte una página de la API en registros RAW, deduplicando dentro de la página.
    window_ts: si se informa, da el valor de last_updated_at_fudo (columna que corta la ventana
    móvil en el swap) en lugar del createdAt del propio registro.
    """
    extracted_at = datetime.now(timezone.utc)
    prepared = {}
    for record in page:
        fudo_id = record.get('id', str(uuid.uuid4()))
        payload_str = json.dumps(record, sort_keys=True)
        checksum = md5(payload_str.encode('utf-8')).hexdigest()

        # Clave de unicidad: ID + Sucursal + Contenido
        unique_key = (fudo_id, checksum)
        if unique_key not in prepared:
            prepared[unique_key] = {
                'id_fudo': fudo_id,
                'id_sucursal_fuente': id_sucursal,
                'fecha_extraccion_utc': extracted_at,
                'payload_json': payload_str,
                # Guarda el createdAt de Fudo: es la columna que delimita la ventana móvil en el swap
                'last_updated_at_fudo': (window_ts(record) if window_ts
                                         else parse_fudo_date(record.get('attributes', {}).get(WINDOW_FIELD))),
                'payload_checksum': checksum
            }
    return list(prepared.values())


def get_window_config() -> tuple[int, bool]:
    """
    (días de la ventana móvil, forzar full refresh).
    INCREMENTAL_WINDOW_DAYS=0 desactiva la ventana. FORCE_FULL_REFRESH=true descarga todo en esta
    corrida: es la única forma de capturar cambios en registros creados antes de la ventana.
    """
    window_days = max(0, int(os.getenv("INCREMENTAL_WINDOW_DAYS", "60")))
    force_full_refresh = os.getenv("FORCE_FULL_REFRESH", "false").lower() == "true"
    return window_days, force_full_refresh


def resolve_window_start(metadata_manager: ETLMetadataManager, api_client: FudoApiClient,
                         id_sucursal: str, entity: str) -> datetime | None:
    """
    Inicio de la ventana móvil para la entidad, o None si corresponde full refresh.
    Se cuenta desde el último checkpoint (no desde ahora): si el job estuvo caído, la ventana se estira.
    Se trunca a segundos porque el filtro de Fudo no acepta fracciones; el mismo valor se usa en la
    API, en el corte de páginas y en el swap, así lo descargado y lo reconciliado coinciden.
    """
    window_days, force_full_refresh = get_window_config()
    if force_full_refresh or window_days == 0 or entity not in api_client.windowed_entities:
        return None
    last_ts = metadata_manager.get_last_extraction_timestamp(id_sucursal, entity)
    if last_ts is None:
        # Primera corrida de la entidad en la sucursal: carga completa
        return None
    child_entity = child_entity_for(entity)
    if child_entity and metadata_manager.get_last_extraction_timestamp(id_sucursal, child_entity) is None:
        # La entidad hija nunca se cargó (ej. subitems recién agregados): una carga completa del padre
        # trae también el histórico de los hijos. Pasa una sola vez por sucursal.
        logger.info(f"    '{entity}': sin checkpoint de '{child_entity}', se descarga completo para cargar su histórico.")
        return None
    return (last_ts - timedelta(days=window_days)).astimezone(timezone.utc).replace(microsecond=0)


def extract_and_load_entity(db_manager: DBManager, api_client: FudoApiClient,
                            metadata_manager: ETLMetadataManager, id_sucursal: str,
                            entity: str, run_started_at: datetime) -> int:
    """
    Extrae una entidad de una sucursal página por página y la carga en staging apenas llega cada página.
    Al final reconcilia staging contra RAW en UNA transacción:
    - Full refresh: todos los datos de la sucursal.
    - Ventana móvil: solo los registros creados desde el inicio de la ventana; lo anterior no se toca.
    Si la entidad trae hijos incluidos (ej. subitems de items), se cargan y reconcilian en su propia
    tabla RAW con la misma ventana.
    Devuelve la cantidad de registros cargados.
    """
    raw_table_name = raw_table_for(entity)
    staging_table = db_manager.ensure_staging_table(raw_table_name)
    child_entity = child_entity_for(entity)
    child_raw_table = raw_table_for(child_entity) if child_entity else None
    child_staging_table = db_manager.ensure_staging_table(child_raw_table) if child_entity else None
    # Limpia restos de una corrida anterior que haya fallado a mitad de camino
    for table in filter(None, (staging_table, child_staging_table)):
        db_manager.execute_query(
            f"DELETE FROM public.{table} WHERE id_sucursal_fuente = %s;", (id_sucursal,)
        )

    window_start = resolve_window_start(metadata_manager, api_client, id_sucursal, entity)
    total_loaded = 0
    child_loaded = 0
    pages = api_client.iter_pages(entity, id_sucursal, window_start)
    for page_number, (page, children) in enumerate(pages, start=1):
        records = prepare_records(page, id_sucursal)
        db_manager.insert_raw_data(staging_table, records)
        total_loaded += len(records)
        if children:
            # El hijo toma el createdAt del padre como corte de ventana: así el swap con ventana
            # reconcilia exactamente los hijos de los padres descargados, aunque el hijo sea más nuevo.
            parent_created = {r['id_fudo']: r['last_updated_at_fudo'] for r in records}
            parent_rel = INCLUDED_CHILDREN[entity]['parent_relationship']
            child_records = prepare_records(
                children, id_sucursal,
                window_ts=lambda c: parent_created.get(c['relationships'][parent_rel]['data']['id']),
            )
            db_manager.insert_raw_data(child_staging_table, child_records)
            child_loaded += len(child_records)
        if page_number % 20 == 0:
            logger.info(f"    '{entity}': {total_loaded} registros cargados hasta la página {page_number}...")

    if total_loaded == 0:
        # No se reconcilia con staging vacío: una respuesta vacía de la API no debe borrar datos de RAW
        logger.info(f"    No hay datos nuevos para '{entity}'.")
        return 0

    scope = f"ventana desde {format_fudo_date(window_start)}" if window_start else "full refresh"
    deleted, inserted = db_manager.swap_branch_from_staging(raw_table_name, staging_table, id_sucursal, window_start)
    logger.info(f"    [AUDIT] '{entity}' reemplazado para la sucursal ({scope}): {total_loaded} registros "
                f"({deleted} borrados, {inserted} insertados).")

    if child_entity:
        # Se reconcilia aunque no haya hijos: con padres descargados, "ningún hijo" es una respuesta válida
        # y así se borran los que ya no existen en Fudo.
        deleted, inserted = db_manager.swap_branch_from_staging(
            child_raw_table, child_staging_table, id_sucursal, window_start
        )
        logger.info(f"    [AUDIT] '{child_entity}' reemplazado para la sucursal ({scope}): {child_loaded} registros "
                    f"({deleted} borrados, {inserted} insertados).")

    # Se guarda el inicio de la corrida (no el final) para no perder registros creados durante la extracción
    metadata_manager.update_last_extraction_timestamp(id_sucursal, entity, run_started_at)
    if child_entity:
        metadata_manager.update_last_extraction_timestamp(id_sucursal, child_entity, run_started_at)
    return total_loaded


def get_worker_counts() -> tuple[int, int]:
    """(sucursales en paralelo, entidades en paralelo por sucursal). Requests simultáneos a Fudo = producto."""
    branch_workers = max(1, int(os.getenv("ETL_BRANCH_WORKERS", "3")))
    entity_workers = max(1, int(os.getenv("ETL_ENTITY_WORKERS", "2")))
    return branch_workers, entity_workers


def authenticate_branches(authenticator: FudoAuthenticator,
                          branches_config: list[tuple]) -> tuple[list[tuple], list[str]]:
    """
    Obtiene el token de cada sucursal antes de extraer.
    Devuelve (sucursales disponibles como (branch_data, token_provider), ids de las omitidas).
    Una sucursal sin credenciales válidas no frena al resto ni cuenta como error del ETL:
    se informa en el log con el prefijo [CREDENCIALES] para poder filtrarla o alertar sobre ella.
    """
    available, skipped = [], []
    for branch_data in branches_config:
        id_sucursal, _, branch_name, api_key_secret_name, api_secret_secret_name = branch_data
        try:
            token_provider = BranchTokenProvider(authenticator, id_sucursal, api_key_secret_name, api_secret_secret_name)
            available.append((branch_data, token_provider))
        except CREDENTIAL_ERRORS as e:
            logger.warning(f"[CREDENCIALES] Sucursal '{branch_name}' ({id_sucursal}) omitida: {e}")
            skipped.append(id_sucursal)
        except Exception as e:
            # Falla inesperada (red, base, respuesta rara de Fudo): se omite igual, pero se deja el detalle
            logger.error(f"[CREDENCIALES] Sucursal '{branch_name}' ({id_sucursal}) omitida: {e}", exc_info=True)
            skipped.append(id_sucursal)

    logger.info(f"[CREDENCIALES] {len(available)}/{len(branches_config)} sucursales con credenciales válidas.")
    if skipped:
        logger.warning(f"[CREDENCIALES] Sucursales omitidas en esta corrida: {', '.join(skipped)}")
    return available, skipped


def extract_branch(db_manager: DBManager, metadata_manager: ETLMetadataManager, api_base_url: str,
                   branch_data: tuple, token_provider: BranchTokenProvider,
                   run_started_at: datetime, entity_workers: int) -> list[str]:
    """
    Extrae todas las entidades de una sucursal ya autenticada, varias a la vez.
    Cada entidad usa su propio FudoApiClient (requests.Session no se comparte entre hilos),
    todas con el mismo token de la sucursal. Nunca lanza: devuelve la lista de fallos.
    Una entidad sin permiso en Fudo (403) se omite con aviso [PERMISOS] y no cuenta como fallo.
    """
    id_sucursal, _, branch_name, _, _ = branch_data
    logger.info(f"--- Procesando Sucursal: '{branch_name}' ({id_sucursal}) ---")

    def run_entity(entity: str):
        api_client = FudoApiClient(api_base_url)
        try:
            api_client.set_auth_token(token_provider.token)
            api_client.token_refresher = lambda: token_provider.refresh(api_client.auth_token)
            extract_and_load_entity(db_manager, api_client, metadata_manager, id_sucursal, entity, run_started_at)
        finally:
            api_client.close()

    failures, forbidden = [], []
    with ThreadPoolExecutor(max_workers=entity_workers, thread_name_prefix=f"{id_sucursal}") as executor:
        futures = {executor.submit(run_entity, entity): entity for entity in ENTITIES_TO_EXTRACT}
        for future in as_completed(futures):
            entity = futures[future]
            try:
                future.result()
            except EntityForbiddenError as e:
                logger.warning(f"[PERMISOS] Entidad '{entity}' (sucursal '{branch_name}') omitida: {e}")
                forbidden.append(entity)
            except Exception as e:
                logger.error(f"  Error en entidad '{entity}' (sucursal '{branch_name}'): {e}", exc_info=True)
                failures.append(f"{id_sucursal}/{entity}")

    if forbidden:
        logger.warning(f"[PERMISOS] Sucursal '{branch_name}' ({id_sucursal}) sin permiso en Fudo para: {', '.join(forbidden)}")
    logger.info(f"--- Sucursal '{branch_name}' finalizada ({len(failures)} fallos, {len(forbidden)} sin permiso) ---")
    return failures


# --- FUNCIÓN PARA LA FASE DE TRANSFORMACIÓN Y CARGA AL DER ---
def refresh_analytics_materialized_views(db_manager: DBManager,
                                          materialized_views_configs: list[tuple[str, str]],
                                          raw_views_configs: list[tuple[str, str]]) -> list[str]:
    """
    Crea las MVs solo si no existen (o si REBUILD_MVS=true) y luego las refresca CONCURRENTLY,
    lo que permite que Power BI siga leyendo durante el refresco.
    Devuelve la lista de objetos que fallaron.
    """
    logger.info("==================================================")
    logger.info("  Iniciando fase de Transformación (Creación/Refresco de MVs y Vistas RAW)")
    logger.info("==================================================")

    rebuild_mvs = os.getenv("REBUILD_MVS", "false").lower() == "true"
    failures = []

    for view_name, create_sql in raw_views_configs:
        logger.info(f"  Procesando Vista RAW Desnormalizada: '{view_name}'...")
        try:
            db_manager.execute_query(create_sql)
        except Exception as e:
            logger.error(f"  ERROR al procesar la Vista RAW '{view_name}': {e}")
            failures.append(view_name)

    for mv_name, create_sql in materialized_views_configs:
        try:
            exists = db_manager.fetch_one(
                "SELECT 1 FROM pg_matviews WHERE schemaname = 'public' AND matviewname = %s;", (mv_name,)
            )
            if rebuild_mvs:
                logger.info(f"  Recreando MV '{mv_name}' (REBUILD_MVS=true)...")
                db_manager.execute_query(create_sql)
            elif not exists:
                logger.info(f"  Creando MV '{mv_name}' (no existía)...")
                db_manager.execute_query(DROP_MV_PATTERN.sub("", create_sql))
            else:
                logger.info(f"  Refrescando MV '{mv_name}' CONCURRENTLY...")
                try:
                    db_manager.execute_query(f"REFRESH MATERIALIZED VIEW CONCURRENTLY public.{mv_name};")
                except (psycopg2.errors.FeatureNotSupported, psycopg2.errors.ObjectNotInPrerequisiteState) as e:
                    # CONCURRENTLY requiere un índice único y que la MV esté poblada
                    logger.warning(f"  No se pudo refrescar '{mv_name}' CONCURRENTLY ({e}). Usando REFRESH normal.")
                    db_manager.execute_query(f"REFRESH MATERIALIZED VIEW public.{mv_name};")
            logger.info(f"  MV '{mv_name}' OK.")
        except Exception as e:
            logger.error(f"  ERROR al procesar la Vista Materializada '{mv_name}': {e}")
            failures.append(mv_name)

    logger.info("==================================================")
    logger.info("  Fase de Transformación (Creación/Refresco de MVs y Vistas RAW) FINALIZADA.")
    logger.info("==================================================")
    return failures


def run_fudo_raw_etl(db_manager: DBManager, client_name: str,
                     materialized_views_configs: list[tuple[str, str]],
                     raw_views_configs: list[tuple[str, str]]) -> list[str]:
    """
    Ejecuta la extracción y carga de todas las sucursales activas y luego la transformación.
    Primero valida las credenciales: las sucursales sin credenciales válidas se omiten y solo
    quedan en el log (no cuentan como error, salvo que no quede ninguna disponible).
    Un fallo en una entidad no frena el resto (sus datos previos quedan intactos),
    pero se registra y se devuelve para que el proceso termine con error.
    """
    logger.info("==================================================")
    logger.info(f"  Iniciando proceso ETL RAW para cliente '{client_name}'")
    logger.info("==================================================")

    run_started_at = datetime.now(timezone.utc)
    config = load_config()
    project_id = config.get("gcp_project_id")
    metadata_manager = ETLMetadataManager(db_manager)
    authenticator = FudoAuthenticator(db_manager, config['fudo_auth_endpoint'], project_id)
    api_base_url = config['fudo_api_base_url']
    failures = []

    branches_config = db_manager.fetch_all(
        "SELECT id_branch, fudo_branch_identifier, branch_name, "
        "secret_manager_apikey_name, secret_manager_apisecret_name "
        "FROM public.config_fudo_branches WHERE is_active = TRUE"
    )
    if not branches_config:
        logger.warning(f"No se encontraron sucursales activas para '{client_name}'.")
        return ["sin_sucursales_activas"]

    # Las tablas staging se crean antes de lanzar los hilos: dos CREATE TABLE IF NOT EXISTS
    # simultáneos sobre la misma tabla pueden fallar en Postgres.
    for entity in ENTITIES_TO_EXTRACT:
        db_manager.ensure_staging_table(raw_table_for(entity))
        if child_entity_for(entity):
            db_manager.ensure_staging_table(raw_table_for(child_entity_for(entity)))

    window_days, force_full_refresh = get_window_config()
    if force_full_refresh:
        logger.info("[VENTANA] FORCE_FULL_REFRESH=true: todas las entidades se descargan completas en esta corrida.")
    elif window_days == 0:
        logger.info("[VENTANA] INCREMENTAL_WINDOW_DAYS=0: ventana móvil desactivada, todo es full refresh.")
    else:
        logger.info(f"[VENTANA] Ventana móvil de {window_days} días (desde el último checkpoint) para: "
                    f"{', '.join(WINDOWED_ENTITIES)}.")

    available_branches, _ = authenticate_branches(authenticator, branches_config)
    if not available_branches:
        logger.error("[CREDENCIALES] Ninguna sucursal tiene credenciales válidas. No se extrae nada.")
        return ["sin_sucursales_con_credenciales"]

    branch_workers, entity_workers = get_worker_counts()
    logger.info(f"Extrayendo {len(available_branches)} sucursales "
                f"({branch_workers} sucursales x {entity_workers} entidades en paralelo).")

    with ThreadPoolExecutor(max_workers=branch_workers, thread_name_prefix="sucursal") as executor:
        futures = [
            executor.submit(extract_branch, db_manager, metadata_manager, api_base_url,
                            branch_data, token_provider, run_started_at, entity_workers)
            for branch_data, token_provider in available_branches
        ]
        for future in as_completed(futures):
            failures.extend(future.result())

    # Las cargas son atómicas por sucursal/entidad, así que las MVs se refrescan
    # aunque alguna entidad haya fallado (esa entidad conserva sus datos anteriores).
    failures.extend(refresh_analytics_materialized_views(db_manager, materialized_views_configs, raw_views_configs))
    return failures


# --- FUNCIÓN PARA DESPLEGAR LA ESTRUCTURA INICIAL DE FUDO EN LA DB ---
def deploy_fudo_database_structure(db_manager: DBManager, client_name: str):
    logger.info("==================================================")
    logger.info(f"  Iniciando despliegue de estructura para cliente '{client_name}'")
    logger.info("==================================================")
    try:
        # 1. Tablas RAW y Metadatos genéricas
        base_raw_ddl = read_sql_file('fudo_etl/sql/base_raw_tables_and_metadata.sql')
        db_manager.execute_sql_script(base_raw_ddl)

        # 2. Tablas Lógicas del DER específicas del cliente
        #client_der_ddl = read_sql_file(f'clients/{client_name}/der_tables_ddl.sql')
        #db_manager.execute_sql_script(client_der_ddl)

        # 3. Datos de sucursales específicos del cliente
        branches_sql = read_sql_file(f'clients/{client_name}/branches.sql')
        db_manager.execute_sql_script(branches_sql)

        logger.info("Estructura desplegada exitosamente.")
    except Exception as e:
        logger.critical(f"ERROR al desplegar estructura: {e}", exc_info=True)
        raise
    logger.info("==================================================")
    logger.info("  Despliegue de estructura Fudo FINALIZADO.")
    logger.info("==================================================")


def main() -> int:
    config = load_config()
    db_conn_string = config['db_connection_string']

    # 1. ¿Qué cliente estamos procesando? Lo leemos del .env
    client_name = os.getenv("CLIENT_NAME")
    if not client_name:
        raise ValueError("La variable de entorno CLIENT_NAME no está definida.")

    logger.info(f"Iniciando ETL GENÉRICO para el cliente: {client_name.upper()}")

    # 2. Configurar Python para que pueda importar desde la carpeta 'clients'
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    clients_dir = os.path.join(base_dir, 'clients')
    if clients_dir not in sys.path:
        sys.path.insert(0, clients_dir)

    db_for_all_phases = None
    exit_code = 0
    try:
        # 3. Importación Dinámica de las Vistas Materializadas del Cliente
        # Esto importa dinámicamente: clients.miguitas.analytical_layer_mvs
        client_mvs_module = importlib.import_module(f"{client_name}.analytical_layer_mvs")
        materialized_views_configs = client_mvs_module.materialized_views_configs
        raw_views_configs = client_mvs_module.raw_views_configs

        # Una conexión por hilo de extracción + una para el hilo principal (metadata, MVs)
        branch_workers, entity_workers = get_worker_counts()
        pool_size = int(os.getenv("DB_POOL_SIZE", str(branch_workers * entity_workers + 1)))
        db_for_all_phases = DBManager(db_conn_string, pool_size=pool_size)

        # 4. Fase de Despliegue DDL
        deploy_fudo_database_structure(db_for_all_phases, client_name)

        # 5. Fase de ETL y MVs
        logger.info("\nIniciando fase de EJECUCIÓN REGULAR del ETL...")
        failures = run_fudo_raw_etl(db_for_all_phases, client_name, materialized_views_configs, raw_views_configs)

        if failures:
            logger.error(f"ETL finalizado CON ERRORES ({len(failures)}): {', '.join(failures)}")
            exit_code = 1
        else:
            logger.info("\n¡Proceso ETL finalizado con éxito!")

    except Exception as e:
        logger.critical(f"ERROR FATAL: {e}", exc_info=True)
        exit_code = 1
    finally:
        if db_for_all_phases:
            db_for_all_phases.close()
        logger.info("==================================================")
        logger.info(f"  FINALIZACIÓN COMPLETA DEL SCRIPT ETL para cliente '{client_name}' (exit code {exit_code}).")
        logger.info("==================================================")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
