# fudo_etl/modules/fudo_api_client.py
import os
import time
import logging
from datetime import datetime, timezone
from typing import Callable, Iterator

from .http_retry import build_retry_session

logger = logging.getLogger(__name__)

# Campo de Fudo que delimita la ventana móvil. Se guarda en RAW como last_updated_at_fudo.
WINDOW_FIELD = 'createdAt'

# Entidades con ventana móvil: solo se descargan los registros creados desde el inicio de la ventana
# y solo se reconcilia esa porción de RAW. Según el spec de Fudo (openapi v1alpha1):
#   'filter'    -> el endpoint acepta filter[createdAt]=gte.<fecha>
#   'sort_desc' -> no tiene filtro, pero admite sort=-createdAt: se pagina de lo más nuevo a lo más
#                  viejo y se corta al pasar el inicio de la ventana
WINDOWED_ENTITIES = {
    'sales': 'filter',
    'payments': 'filter',
    'expenses': 'filter',
    'items': 'sort_desc',
}

# Registros hijos que no tienen endpoint propio y solo llegan con include=... en la entidad padre.
# Los subitems son los modificadores de un item (ej. "Empanadas calientes por unidad" + 12 "Emp. Carne"):
# /v1alpha1/subitems responde 404, pero /items?include=subitems los trae en 'included'.
INCLUDED_CHILDREN = {
    'items': {'include': 'subitems', 'type': 'Subitem', 'parent_relationship': 'item'},
}


def parse_fudo_date(date_str: str | None) -> datetime | None:
    """Parsea una fecha de Fudo (ISO 8601 con 'Z') a datetime UTC. Devuelve None si falta o no se puede parsear."""
    if date_str is None:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f"No se pudo parsear la fecha de Fudo: '{date_str}'. Retornando None.")
        return None


def format_fudo_date(ts: datetime) -> str:
    """Formatea un datetime como lo aceptan los filtros de Fudo: UTC, sin fracción de segundo y con 'Z'."""
    return ts.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _created_before(record: dict, ts: datetime) -> bool:
    """True si el registro fue creado antes de ts. Sin fecha válida se considera dentro de la ventana."""
    created_at = parse_fudo_date(record.get('attributes', {}).get(WINDOW_FIELD))
    return created_at is not None and created_at < ts


class EntityDeadlineExceeded(TimeoutError):
    """La extracción de una entidad superó su tiempo máximo permitido."""


class EntityForbiddenError(PermissionError):
    """Fudo respondió 403: el usuario API de la sucursal no tiene permiso sobre la entidad."""


class FudoApiClient:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.auth_token = None
        # 500 es el máximo real: si se piden más, Fudo devuelve solo 250 sin avisar y la
        # paginación cortaría antes de tiempo (len(data) < page_size) perdiendo datos.
        self.page_size = 500
        # Pausa preventiva entre páginas; los 429 igual los maneja el Retry respetando Retry-After
        self.inter_page_delay = float(os.getenv("API_INTER_PAGE_DELAY_SECONDS", "0.15"))
        # (connect, read) en segundos
        self.request_timeout = (5, 30)
        # Tiempo máximo total para extraer una entidad de una sucursal
        self.entity_deadline_seconds = int(os.getenv("API_ENTITY_DEADLINE_SECONDS", "1800"))

        # Reintentos ante errores transitorios, respetando Retry-After (con tope)
        self.session = build_retry_session({"GET"})
        # Función que devuelve un token nuevo; se usa para recuperarse de un 401 a mitad de corrida
        self.token_refresher: Callable[[], str] | None = None

        # --- Mapeo EXPLÍCITO: SOLO para las que SÍ necesitan fields para traer datos extra ---
        # No incluimos 'products' ni 'customers' aquí para que Fudo mande el JSON COMPLETO por defecto.
        self.fields_key_mapping = {
            'expenses': 'expense',
            'expense-categories': 'expenseCategory',
            'providers': 'provider' # Nuevo campo solicitado
        }

        self.fields_parameters = {
            'expense': 'amount,canceled,cashRegister,createdAt,date,description,dueDate,expenseCategory,expenseItems,paymentDate,paymentMethod,provider,receiptNumber,receiptType,status,useInCashCount,user',
            'expenseCategory': 'active,financialCategory,name,parentCategory',
            'provider': 'name,email,address,phone,comment,active,internal,providerHouseAccountBalance,fiscalNumber',
        }

        # --- Entidades que siempre se descargan completas ---
        # Son catálogos chicos o entidades sin filtro por fecha en la API: bajarlas enteras es la
        # única forma de detectar cambios. Nunca se les manda un filter[...] (Fudo responde 400).
        self.entities_for_full_refresh = [
            'payment-methods', 'product-categories',
            'product-modifiers', 'products', 'customers', 'discounts',
            'ingredients', 'kitchens', 'roles', 'rooms',
            'tables', 'users', 'providers', 'expense-categories'
        ]

        # --- Entidades con ventana móvil por createdAt (ver WINDOWED_ENTITIES) ---
        self.windowed_entities = WINDOWED_ENTITIES

    def set_auth_token(self, token: str):
        self.auth_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"
        logger.debug("Token de autenticación establecido.")

    def close(self):
        self.session.close()

    def iter_pages(self, entity_name: str, id_sucursal: str,
                   window_start: datetime | None = None) -> Iterator[tuple[list[dict], list[dict]]]:
        """
        Extrae datos de la API de Fudo y devuelve un generador de páginas (registros, hijos incluidos).
        Así nunca se mantiene en memoria más de una página por vez.
        - window_start None: trae la entidad completa (full refresh).
        - window_start informado (solo entidades de 'windowed_entities'): trae únicamente los
          registros con createdAt >= window_start.
        - Hijos: solo para entidades de INCLUDED_CHILDREN (ej. subitems de items); vacío para el resto.
        """
        if not self.auth_token:
            raise ValueError("Token de autenticación no establecido.")

        window_mode = self.windowed_entities.get(entity_name) if window_start else None
        params = {}
        stop_before = None

        if window_mode == 'filter':
            params[f'filter[{WINDOW_FIELD}]'] = f"gte.{format_fudo_date(window_start)}"
        elif window_mode == 'sort_desc':
            params['sort'] = f"-{WINDOW_FIELD}"
            stop_before = window_start

        if window_mode:
            logger.info(f"--- ESTRATEGIA VENTANA ({window_mode}) desde {format_fudo_date(window_start)}: {entity_name} ---")
        else:
            logger.info(f"--- ESTRATEGIA FULL REFRESH: {entity_name} ---")

        # Filtro de campos (Solo si está definido en el mapeo)
        fields_key = self.fields_key_mapping.get(entity_name)
        fields_params = self.fields_parameters.get(fields_key or '')
        if fields_key and fields_params:
            params[f'fields[{fields_key}]'] = fields_params

        child = INCLUDED_CHILDREN.get(entity_name)
        if child:
            params['include'] = child['include']

        return self._iter_paginated_data_generic(
            request_url=f"{self.api_base_url}/v1alpha1/{entity_name}",
            entity_name=entity_name,
            params=params,
            stop_before=stop_before,
            child=child,
        )

    def _iter_paginated_data_generic(self, request_url, entity_name, params: dict,
                                     stop_before: datetime | None = None, child: dict | None = None,
                                     start_page=1, max_pages=-1) -> Iterator[tuple[list[dict], list[dict]]]:
        """
        Pagina el endpoint hasta la última página. Devuelve (registros, hijos) por página.
        stop_before: solo para endpoints ordenados por createdAt descendente. Descarta los registros
        creados antes de esa fecha y corta la paginación en la primera página que los contiene.
        child: entrada de INCLUDED_CHILDREN. Se devuelven los 'included' de ese tipo cuyo padre
        quedó entre los registros devueltos (los de padres descartados por stop_before no van).
        """

        deadline = time.monotonic() + self.entity_deadline_seconds
        current_page = start_page

        while max_pages == -1 or current_page < start_page + max_pages:
            if time.monotonic() > deadline:
                raise EntityDeadlineExceeded(
                    f"'{entity_name}' superó el deadline de {self.entity_deadline_seconds}s (página {current_page})."
                )

            current_params = params.copy()
            current_params['page[size]'] = self.page_size
            current_params['page[number]'] = current_page

            # Los reintentos transitorios los maneja el HTTPAdapter; si se agotan, la excepción sube.
            response = self.session.get(request_url, params=current_params, timeout=self.request_timeout)
            if response.status_code == 401 and self.token_refresher:
                # Token vencido o revocado a mitad de la extracción: se renueva una vez y se repite la página
                logger.warning(f"401 en {entity_name} (página {current_page}). Renovando token y reintentando.")
                self.set_auth_token(self.token_refresher())
                response = self.session.get(request_url, params=current_params, timeout=self.request_timeout)
            if response.status_code == 403:
                # Falta de permisos del rol en Fudo, no un fallo del ETL: lo informa quien llama como aviso
                raise EntityForbiddenError(f"403 Forbidden en '{entity_name}' (página {current_page}): {response.text[:200]}")
            if not response.ok:
                logger.error(f"Error {response.status_code} en {entity_name} (página {current_page}): {response.text[:500]}")
                response.raise_for_status()

            body = response.json()
            data = body.get('data', [])
            reached_window_start = False
            if stop_before is not None and data:
                in_window = [record for record in data if not _created_before(record, stop_before)]
                reached_window_start = len(in_window) < len(data)
                data_to_yield = in_window
            else:
                data_to_yield = data

            children = []
            if child and data_to_yield:
                parent_ids = {record.get('id') for record in data_to_yield}
                rel = child['parent_relationship']
                children = [
                    inc for inc in body.get('included') or []
                    if inc.get('type') == child['type']
                    and ((inc.get('relationships', {}).get(rel) or {}).get('data') or {}).get('id') in parent_ids
                ]

            if data_to_yield:
                yield data_to_yield, children
            if reached_window_start:
                logger.info(f"    '{entity_name}': se alcanzó el inicio de la ventana en la página {current_page}.")
                return
            if not data or len(data) < self.page_size:
                return

            current_page += 1
            time.sleep(self.inter_page_delay)
