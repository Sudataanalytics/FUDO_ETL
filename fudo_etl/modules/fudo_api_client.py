# fudo_etl/modules/fudo_api_client.py
import os
import time
import logging
from datetime import datetime, timezone
from typing import Callable, Iterator

from .http_retry import build_retry_session

logger = logging.getLogger(__name__)


class EntityDeadlineExceeded(TimeoutError):
    """La extracción de una entidad superó su tiempo máximo permitido."""


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

        # --- Entidades que siempre se descargan completas (Para evitar errores 400 de filtro) ---
        self.entities_for_full_refresh = [
            'sales', 'payments', 'payment-methods', 'product-categories',
            'product-modifiers', 'products', 'customers', 'discounts',
            'ingredients', 'items', 'kitchens', 'roles', 'rooms',
            'tables', 'users', 'providers', 'expense-categories'
        ]

        # --- Entidades con filtro incremental ---
        self.incremental_filter_entities = {
            'sales': 'createdAt',
        }

    def set_auth_token(self, token: str):
        self.auth_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"
        logger.debug("Token de autenticación establecido.")

    def close(self):
        self.session.close()

    def iter_pages(self, entity_name: str, id_sucursal: str, last_extracted_ts: datetime = None) -> Iterator[list[dict]]:
        """
        Extrae datos de la API de Fudo y devuelve un generador de páginas (listas de registros).
        Así nunca se mantiene en memoria más de una página por vez.
        Si la entidad está en 'entities_for_full_refresh', ignora el timestamp y trae todo.
        """
        if not self.auth_token:
            raise ValueError("Token de autenticación no establecido.")

        is_full_refresh = entity_name in self.entities_for_full_refresh
        apply_filter = (not is_full_refresh and last_extracted_ts is not None)

        if is_full_refresh:
            logger.info(f"--- ESTRATEGIA FULL REFRESH: {entity_name} ---")
        else:
            logger.info(f"--- ESTRATEGIA INCREMENTAL: {entity_name} ---")

        fields_key = self.fields_key_mapping.get(entity_name)
        return self._iter_paginated_data_generic(
            request_url=f"{self.api_base_url}/v1alpha1/{entity_name}",
            entity_name=entity_name,
            apply_incremental_filter=apply_filter,
            incremental_filter_ts=last_extracted_ts,
            fields_key=fields_key,
            fields_params=self.fields_parameters.get(fields_key or ''),
        )

    def _iter_paginated_data_generic(self, request_url, entity_name, apply_incremental_filter,
                                     incremental_filter_ts=None, fields_key=None, fields_params=None,
                                     start_page=1, max_pages=-1) -> Iterator[list[dict]]:
        params = {}

        # Filtro de fecha
        if apply_incremental_filter and incremental_filter_ts:
            filter_field = self.incremental_filter_entities.get(entity_name, 'createdAt')
            formatted_ts = incremental_filter_ts.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
            params[f'filter[{filter_field}]'] = f"gte.{formatted_ts}"

        # Filtro de campos (Solo si está definido en el mapeo)
        if fields_key and fields_params:
            params[f'fields[{fields_key}]'] = fields_params

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
            if not response.ok:
                logger.error(f"Error {response.status_code} en {entity_name} (página {current_page}): {response.text[:500]}")
                response.raise_for_status()

            data = response.json().get('data', [])
            if data:
                yield data
            if not data or len(data) < self.page_size:
                return

            current_page += 1
            time.sleep(self.inter_page_delay)
