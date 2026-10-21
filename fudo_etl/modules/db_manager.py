# fudo_etl/modules/db_manager.py
import os
import time
import logging
import threading
from contextlib import contextmanager
from functools import wraps

import psycopg2
from psycopg2 import extensions, extras, pool

logger = logging.getLogger(__name__)

RAW_COLUMNS = [
    'id_fudo', 'id_sucursal_fuente', 'fecha_extraccion_utc',
    'payload_json', 'last_updated_at_fudo', 'payload_checksum'
]


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _retry_on_operational_error(method):
    """
    Reintenta con backoff ante errores de conexión / lock timeout.
    Solo se aplica a operaciones idempotentes: cada método corre en su propia
    transacción, que se revierte completa ante un fallo, así que repetirla es seguro.
    No reintenta statement_timeout (QueryCanceledError): repetir una consulta lenta no ayuda.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        attempt = 1
        while True:
            try:
                return method(self, *args, **kwargs)
            except psycopg2.extensions.QueryCanceledError:
                raise
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt >= self.max_retries:
                    logger.error(f"{method.__name__}: agotados {self.max_retries} intentos. Último error: {e}")
                    raise
                delay = min(self.retry_base_delay * (2 ** (attempt - 1)), 60)
                logger.warning(f"{method.__name__}: error de base de datos ({e}). "
                               f"Reintento {attempt}/{self.max_retries - 1} en {delay}s.")
                time.sleep(delay)
                attempt += 1
    return wrapper


class DBManager:
    """
    Acceso a PostgreSQL thread-safe mediante un pool de conexiones.
    Cada operación toma una conexión del pool, corre en su propia transacción y la devuelve.
    Una conexión que falla con error de conexión se descarta y el reintento usa otra (o abre una nueva).
    """

    def __init__(self, connection_string: str, pool_size: int | None = None):
        self.connection_string = connection_string
        self.max_retries = _env_int("DB_MAX_RETRIES", 4)
        self.retry_base_delay = _env_int("DB_RETRY_BASE_DELAY_SECONDS", 2)
        # Timeouts del lado del servidor (ms). Evitan que el ETL quede colgado esperando un lock
        # (ej. Power BI leyendo una tabla) o una consulta que no termina nunca.
        self.statement_timeout_ms = _env_int("DB_STATEMENT_TIMEOUT_MS", 15 * 60 * 1000)
        self.lock_timeout_ms = _env_int("DB_LOCK_TIMEOUT_MS", 30 * 1000)
        self.idle_in_tx_timeout_ms = _env_int("DB_IDLE_IN_TX_TIMEOUT_MS", 5 * 60 * 1000)
        # Una conexión que estuvo ociosa más que esto se valida con SELECT 1 antes de usarla
        self.ping_after_idle_seconds = _env_int("DB_POOL_PING_AFTER_IDLE_SECONDS", 60)
        self.pool_size = pool_size or _env_int("DB_POOL_SIZE", 4)

        self._pool = None
        # ThreadedConnectionPool no bloquea cuando se agota (lanza PoolError): el semáforo hace esperar
        self._slots = threading.BoundedSemaphore(self.pool_size)
        self._last_used: dict[int, float] = {}
        self._last_used_lock = threading.Lock()
        self._create_pool_with_retry()

    def _create_pool(self):
        # minconn = maxconn: psycopg2 cierra (en vez de reusar) las conexiones devueltas por encima de minconn
        self._pool = pool.ThreadedConnectionPool(
            self.pool_size, self.pool_size,
            self.connection_string,
            connect_timeout=10,
            application_name="fudo_etl",
            # Keepalives TCP: detectan conexiones cortadas por NAT/firewall mientras se extrae de la API
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
            tcp_user_timeout=60000,
            options=(
                f"-c statement_timeout={self.statement_timeout_ms} "
                f"-c lock_timeout={self.lock_timeout_ms} "
                f"-c idle_in_transaction_session_timeout={self.idle_in_tx_timeout_ms}"
            ),
        )
        logger.info(f"Pool de conexiones PostgreSQL creado ({self.pool_size} conexiones).")

    @_retry_on_operational_error
    def _create_pool_with_retry(self):
        self._create_pool()

    def _is_alive(self, conn) -> bool:
        """Valida con SELECT 1 una conexión que estuvo ociosa mucho tiempo (puede haberla cortado el servidor)."""
        if conn.closed:
            return False
        with self._last_used_lock:
            last_used = self._last_used.get(id(conn))
        if last_used is None or time.monotonic() - last_used < self.ping_after_idle_seconds:
            return True
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
            conn.rollback()
            return True
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            return False

    def _discard(self, conn):
        """Saca una conexión rota del pool; el pool abre una nueva cuando haga falta."""
        with self._last_used_lock:
            self._last_used.pop(id(conn), None)
        try:
            self._pool.putconn(conn, close=True)
        except Exception:
            pass

    @contextmanager
    def _connection(self):
        """
        Presta una conexión del pool. Al devolverla, si quedó cerrada o en un estado distinto de IDLE
        (ej. se cortó a mitad de transacción) se descarta en lugar de volver al pool.
        Un lock timeout no la descarta: la conexión sigue sana después del rollback.
        """
        with self._slots:
            conn = self._pool.getconn()
            if not self._is_alive(conn):
                logger.warning("Conexión del pool caída. Se descarta y se abre una nueva.")
                self._discard(conn)
                conn = self._pool.getconn()
            try:
                yield conn
            finally:
                if conn.closed or conn.info.transaction_status != extensions.TRANSACTION_STATUS_IDLE:
                    self._discard(conn)
                else:
                    with self._last_used_lock:
                        self._last_used[id(conn)] = time.monotonic()
                    self._pool.putconn(conn)

    def close(self):
        """Cierra todas las conexiones del pool."""
        if self._pool is not None and not self._pool.closed:
            self._pool.closeall()
            logger.info("Pool de conexiones PostgreSQL cerrado.")

    def _run(self, fn):
        """Ejecuta fn(cursor) en una transacción: commit al final, rollback ante cualquier error."""
        with self._connection() as conn:
            try:
                with conn.cursor() as cursor:
                    result = fn(cursor)
                conn.commit()
                return result
            except Exception:
                if not conn.closed:
                    try:
                        conn.rollback()
                    except (psycopg2.OperationalError, psycopg2.InterfaceError):
                        pass
                raise

    @_retry_on_operational_error
    def execute_query(self, query: str, params: tuple = None):
        """Ejecuta una consulta SQL que no devuelve resultados y hace commit."""
        try:
            self._run(lambda cur: cur.execute(query, params))
            logger.debug(f"Consulta ejecutada con éxito: {query[:100]}...")
        except Exception as e:
            logger.error(f"Error al ejecutar la consulta: {e}. Query: {query[:100]}...")
            raise

    @_retry_on_operational_error
    def execute_upsert(self, query: str, params: tuple | list[tuple]):
        """Ejecuta una consulta SQL de UPSERT."""
        def _do(cursor):
            if isinstance(params, list):
                extras.execute_values(cursor, query, params, page_size=1000)
            else:
                cursor.execute(query, params)
        try:
            self._run(_do)
            logger.debug(f"UPSERT ejecutado con éxito: {query[:100]}...")
        except Exception as e:
            logger.error(f"Error en UPSERT: {e}. Query: {query[:100]}...")
            raise

    @_retry_on_operational_error
    def fetch_one(self, query: str, params: tuple = None) -> tuple | None:
        """Ejecuta una consulta SQL y devuelve una sola fila."""
        def _do(cursor):
            cursor.execute(query, params)
            return cursor.fetchone()
        return self._run(_do)

    @_retry_on_operational_error
    def fetch_all(self, query: str, params: tuple = None) -> list[tuple]:
        """Ejecuta una consulta SQL y devuelve todas las filas."""
        def _do(cursor):
            cursor.execute(query, params)
            return cursor.fetchall()
        return self._run(_do)

    @_retry_on_operational_error
    def execute_sql_script(self, sql_content: str):
        """Ejecuta un script SQL completo."""
        self._run(lambda cur: cur.execute(sql_content))
        logger.info("Script SQL ejecutado exitosamente.")

    @_retry_on_operational_error
    def execute_in_transaction(self, statements: list[tuple[str, tuple | None]]):
        """Ejecuta varias sentencias en UNA sola transacción (todo o nada)."""
        def _do(cursor):
            for query, params in statements:
                cursor.execute(query, params)
        self._run(_do)

    # ----------------------------------------------------------------------
    # CARGA DE DATOS RAW
    # ----------------------------------------------------------------------

    @_retry_on_operational_error
    def insert_raw_data(self, table_name: str, records: list[dict]):
        """
        Inserta un lote de registros RAW. Es idempotente gracias al
        ON CONFLICT (id_fudo, id_sucursal_fuente, payload_checksum) DO NOTHING.
        """
        if not records:
            return

        values_to_insert = [tuple(record.get(col) for col in RAW_COLUMNS) for record in records]
        insert_query = f"""
            INSERT INTO public.{table_name} ({', '.join(RAW_COLUMNS)})
            VALUES %s
            ON CONFLICT (id_fudo, id_sucursal_fuente, payload_checksum) DO NOTHING;
        """
        try:
            self._run(lambda cur: extras.execute_values(cur, insert_query, values_to_insert, page_size=1000))
            logger.debug(f"Cargados {len(records)} registros en {table_name}.")
        except Exception as e:
            logger.error(f"Error al cargar datos en {table_name}: {e}")
            raise

    def ensure_staging_table(self, raw_table_name: str) -> str:
        """Crea (si no existe) la tabla staging UNLOGGED con la misma estructura y PK que la RAW."""
        staging_table = f"stg_{raw_table_name}"
        self.execute_query(
            f"CREATE UNLOGGED TABLE IF NOT EXISTS public.{staging_table} "
            f"(LIKE public.{raw_table_name} INCLUDING ALL);"
        )
        return staging_table

    def swap_branch_from_staging(self, raw_table_name: str, staging_table: str, id_sucursal: str):
        """
        Reemplaza los datos de UNA sucursal en la tabla RAW con los de staging, en una sola transacción.
        Si algo falla, la tabla RAW queda exactamente como estaba (sin ventana de datos vacíos).
        """
        cols = ', '.join(RAW_COLUMNS)
        self.execute_in_transaction([
            (f"DELETE FROM public.{raw_table_name} WHERE id_sucursal_fuente = %s;", (id_sucursal,)),
            (f"INSERT INTO public.{raw_table_name} ({cols}) "
             f"SELECT {cols} FROM public.{staging_table} WHERE id_sucursal_fuente = %s "
             f"ON CONFLICT (id_fudo, id_sucursal_fuente, payload_checksum) DO NOTHING;", (id_sucursal,)),
            (f"DELETE FROM public.{staging_table} WHERE id_sucursal_fuente = %s;", (id_sucursal,)),
        ])
