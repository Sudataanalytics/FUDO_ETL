# fudo_etl/main.py
import logging
import json
from datetime import datetime, timezone
import uuid
import time
from hashlib import md5
import os
import sys         # Importar sys para manejar sys.path
import importlib   # Importar importlib para la importación dinámica

import psycopg2

# Tus módulos (importaciones directas/relativas a la raíz del WORKDIR /app en Docker)
from modules.config import load_config
from modules.db_manager import DBManager
from modules.etl_metadata_manager import ETLMetadataManager
from modules.fudo_auth import FudoAuthenticator
from modules.fudo_api_client import FudoApiClient

# Configuración básica de logging para todo el script principal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Función auxiliar para parsear fechas de la API
def parse_fudo_date(date_str: str | None) -> datetime | None:
    """
    Parsea una cadena de fecha de Fudo (ISO 8601 con 'Z') a un objeto datetime UTC.
    Maneja None y errores de formato.
    """
    if date_str is None:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f"No se pudo parsear la fecha de Fudo: '{date_str}'. Retornando None.")
        return None

# Nueva función para leer el contenido de un archivo SQL
def read_sql_file(relative_path: str) -> str:
    """Lee un archivo SQL desde la raíz del proyecto."""
    # Sube un nivel desde fudo_etl/modules o fudo_etl/main.py hasta la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    absolute_path = os.path.join(base_dir, relative_path)
    with open(absolute_path, 'r', encoding='utf-8') as f:
        return f.read()

# --- FUNCIÓN PARA LA FASE DE TRANSFORMACIÓN Y CARGA AL DER ---
# Ahora recibe las configuraciones de MVs y Vistas RAW como parámetros
def refresh_analytics_materialized_views(db_manager: DBManager,
                                          materialized_views_configs: list[tuple[str, str]],
                                          raw_views_configs: list[tuple[str, str]]):
    logger.info("==================================================")
    logger.info("  Iniciando fase de Transformación (Creación/Refresco de MVs y Vistas RAW)")
    logger.info("==================================================")

    # Iterar para crear/reemplazar las vistas RAW (usando las configs del cliente)
    for view_name, create_sql in raw_views_configs:
        logger.info(f"  Procesando Vista RAW Desnormalizada: '{view_name}'...")
        try:
            db_manager.execute_query(create_sql)
            logger.info(f"  Vista RAW '{view_name}' creada/reemplazada exitosamente.")
        except Exception as e:
            logger.error(f"  ERROR al procesar la Vista RAW '{view_name}': {e}", exc_info=True)
            continue

    # Luego, las MVs del DER (usando las configs del cliente)
    for mv_name, create_sql in materialized_views_configs:
        logger.info(f"  Procesando Vista Materializada: '{mv_name}'...")
        try:
            logger.info(f"    Intentando crear MV '{mv_name}' si no existe...")
            db_manager.execute_query(create_sql)
            logger.info(f"    MV '{mv_name}' creada/existente.")

            # --- CORRECCIÓN CRÍTICA AQUÍ: Usar REFRESH CONCURRENTLY ---
            logger.info(f"    Refrescando MV '{mv_name}' CONCURRENTLY...")
            db_manager.execute_query(f"REFRESH MATERIALIZED VIEW CONCURRENTLY public.{mv_name};")
            logger.info(f"    MV '{mv_name}' refrescada exitosamente.")
            # --------------------------------------------------------

        except psycopg2.errors.LockNotAvailable as e:
            logger.warning(f"  Advertencia: No se pudo adquirir bloqueo para REFRESH CONCURRENTLY de '{mv_name}'. Intentando REFRESH normal. Error: {e}")
            try:
                db_manager.execute_query(f"REFRESH MATERIALIZED VIEW public.{mv_name};")
                logger.info(f"    MV '{mv_name}' refrescada exitosamente (modo normal).")
            except Exception as e_normal:
                logger.error(f"  ERROR (normal) al refrescar la Vista Materializada '{mv_name}': {e_normal}", exc_info=True)
                continue
        except Exception as e:
            logger.error(f"  ERROR al procesar la Vista Materializada '{mv_name}': {e}", exc_info=True)
            continue 

    logger.info("==================================================")
    logger.info("  Fase de Transformación (Creación/Refresco de MVs y Vistas RAW) FINALIZADA.")
    logger.info("==================================================")

# run_fudo_raw_etl ahora recibe el nombre del cliente y las configuraciones de MVs/Vistas RAW
def run_fudo_raw_etl(db_manager: DBManager, client_name: str,
                      materialized_views_configs: list[tuple[str, str]],
                      raw_views_configs: list[tuple[str, str]]):
    logger.info("==================================================")
    logger.info(f"  Iniciando proceso ETL RAW para cliente '{client_name}'")
    logger.info("==================================================")
    
    try:
        config = load_config()
        project_id = config.get("gcp_project_id")
        metadata_manager = ETLMetadataManager(db_manager)
        authenticator = FudoAuthenticator(db_manager, config['fudo_auth_endpoint'], project_id)
        api_client = FudoApiClient(config['fudo_api_base_url'])

        branches_config = db_manager.fetch_all(
            "SELECT id_sucursal, fudo_branch_identifier, sucursal_name, "
            "secret_manager_apikey_name, secret_manager_apisecret_name "
            "FROM public.config_fudo_branches WHERE is_active = TRUE"
        )
        if not branches_config:
            logger.warning(f"No se encontraron sucursales activas para '{client_name}'.")
            return 

        entities_to_extract = [
            'customers', 'discounts', 'expenses', 'expense-categories', 'ingredients',
            'items', 'kitchens', 'payments', 'payment-methods', 'product-categories',
            'product-modifiers', 'products', 'roles', 'rooms', 'sales', 'tables', 'users',
            'providers'
        ]
        
        # --- LÓGICA DE ACUMULACIÓN: Rastrear qué tablas ya limpiamos en esta corrida ---
        tablas_ya_truncadas = set()

        for branch_data in branches_config:
            id_sucursal_internal = branch_data[0]
            branch_name = branch_data[2]
            api_key_secret_name = branch_data[3]
            api_secret_secret_name = branch_data[4]

            logger.info(f"\n--- Procesando Sucursal: '{branch_name}' ({id_sucursal_internal}) ---")

            try:
                token = authenticator.get_valid_token(id_sucursal_internal, api_key_secret_name, api_secret_secret_name)
                api_client.set_auth_token(token)

                for entity in entities_to_extract:
                    raw_table_name = f"fudo_raw_{entity.replace('-', '_')}"
                    
                    try:
                        last_ts = metadata_manager.get_last_extraction_timestamp(id_sucursal_internal, entity)
                        raw_data_records_from_api = api_client.get_data(entity, id_sucursal_internal, last_ts)
                        
                        if raw_data_records_from_api:
                            prepared_records_for_db = []
                            for record in raw_data_records_from_api:
                                payload_str = json.dumps(record, sort_keys=True)
                                prepared_records_for_db.append({
                                    'id_fudo': record.get('id'),
                                    'id_sucursal_fuente': id_sucursal_internal,
                                    'fecha_extraccion_utc': datetime.now(timezone.utc),
                                    'payload_json': payload_str,
                                    'last_updated_at_fudo': parse_fudo_date(record.get('attributes', {}).get('createdAt')),
                                    'payload_checksum': md5(payload_str.encode('utf-8')).hexdigest()
                                })
                            
                            # --- CARGA INTELIGENTE ---
                            if entity in api_client.entities_for_full_refresh:
                                # SOLO truncamos si es la PRIMERA VEZ que esta tabla aparece en TODA la ejecución
                                if raw_table_name not in tablas_ya_truncadas:
                                    logger.info(f"    [AUDIT] TRUNCANDO '{raw_table_name}' (Primera sucursal detectada).")
                                    db_manager.execute_query(f"TRUNCATE TABLE public.{raw_table_name} CASCADE;")
                                    tablas_ya_truncadas.add(raw_table_name)
                                
                                # Insertamos (esto irá sumando las sucursales una debajo de otra)
                                db_manager.insert_raw_data(raw_table_name, prepared_records_for_db)
                                logger.info(f"    [AUDIT] '{entity}' cargados: {len(prepared_records_for_db)} (Acumulando sucursal).")
                            else:
                                # Incremental normal
                                db_manager.insert_raw_data(raw_table_name, prepared_records_for_db)
                            
                            metadata_manager.update_last_extraction_timestamp(id_sucursal_internal, entity, datetime.now(timezone.utc))
                        else:
                            logger.info(f"    No hay datos nuevos para '{entity}'.")
                    except Exception as e:
                        logger.error(f"  Error en entidad '{entity}': {e}")
                        continue
            except Exception as e:
                logger.error(f"Fallo crítico en sucursal '{branch_name}': {e}")
                continue
            time.sleep(1)

        # Al terminar de recorrer todas las sucursales, refrescamos las vistas
        refresh_analytics_materialized_views(db_manager, materialized_views_configs, raw_views_configs)

    except Exception as e:
        logger.critical(f"ERROR FATAL: {e}", exc_info=True)
            
# --- FUNCIÓN PARA DESPLEGAR LA ESTRUCTURA INICIAL DE FUDO EN LA DB ---
# Ahora deploy_fudo_database_structure también recibe el nombre del cliente
def deploy_fudo_database_structure(db_manager: DBManager, client_name: str):
    logger.info("==================================================")
    logger.info(f"  Iniciando despliegue de estructura para cliente '{client_name}'")
    logger.info("==================================================")
    try:
        # 1. Tablas RAW y Metadatos genéricas
        base_raw_ddl = read_sql_file('fudo_etl/sql/base_raw_tables_and_metadata.sql')
        db_manager.execute_sql_script(base_raw_ddl)
        
        # 2. Tablas Lógicas del DER específicas del cliente
        client_der_ddl = read_sql_file(f'clients/{client_name}/der_tables_ddl.sql')
        db_manager.execute_sql_script(client_der_ddl)
        
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


if __name__ == "__main__":
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
    try:
        db_for_all_phases = DBManager(db_conn_string)

        # 3. Importación Dinámica de las Vistas Materializadas del Cliente
        try:
            # Esto importa dinámicamente: clients.miguitas.analytical_layer_mvs
            client_mvs_module = importlib.import_module(f"{client_name}.analytical_layer_mvs")
            materialized_views_configs = client_mvs_module.materialized_views_configs
            raw_views_configs = client_mvs_module.raw_views_configs
        except ImportError as e:
            logger.critical(f"No se encontró la configuración analítica para {client_name}: {e}")
            raise

        # 4. Fase de Despliegue DDL
        deploy_fudo_database_structure(db_for_all_phases, client_name)

        # 5. Fase de ETL y MVs (Asegúrate de modificar run_fudo_raw_etl para que reciba 
        #    'materialized_views_configs' y 'raw_views_configs' como parámetros y se los pase a refresh_analytics...)
        logger.info("\nIniciando fase de EJECUCIÓN REGULAR del ETL...")
        run_fudo_raw_etl(db_for_all_phases, client_name, materialized_views_configs, raw_views_configs)
        
        logger.info("\n¡Proceso ETL finalizado con éxito!")

    except Exception as e:
        logger.critical(f"ERROR FATAL: {e}", exc_info=True)
    finally:
        if db_for_all_phases:
            db_for_all_phases.close()
        logger.info("==================================================")
        logger.info(f"  FINALIZACIÓN COMPLETA DEL SCRIPT ETL para cliente '{client_name}'.")
        logger.info("==================================================")