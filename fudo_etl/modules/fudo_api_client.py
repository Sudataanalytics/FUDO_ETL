import requests
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class FudoApiClient:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.auth_token = None
        self.max_retries = 15
        self.initial_backoff_delay = 5
        self.max_backoff_delay = 300
        self.inter_page_delay = 1.0
        
        # --- Mapeo EXPLÍCITO: SOLO PARA ENTIDADES QUE SOPORTAN 'fields' ---
        self.fields_key_mapping = {
            'expenses': 'expense',
            'expense-categories': 'expenseCategory',
            'payments': 'payment',
            'providers': 'provider', # Para el nuevo endpoint de proveedores
        }

        self.fields_parameters = {
            'expense': 'amount,canceled,cashRegister,createdAt,date,description,dueDate,expenseCategory,expenseItems,paymentDate,paymentMethod,payments,provider,receiptNumber,receiptType,status,useInCashCount,user',
            'expenseCategory': 'active,financialCategory,name,parentCategory',
            'payment': 'amount,canceled,createdAt,externalReference,sale,expense,paymentMethod',
            'provider': 'name,email,address,phone,comment,active,internal,providerHouseAccountBalance,fiscalNumber',
        }

        # --- ENTIDADES PARA FULL REFRESH (NO SOPORTAN FILTRO INCREMENTAL POR FECHA) ---
        # ¡ESTA ES LA LISTA QUE FALTABA Y CAUSABA EL ERROR!
        self.entities_for_full_refresh =[
            'sales',
            'payments',
            'payment-methods',
            'product-categories',
            'product-modifiers',
            'products',
            'customers',
            'discounts',
            'ingredients',
            'items',
            'kitchens',
            'roles',
            'rooms',
            'tables',
            'users',
            'providers', # También va a full refresh porque la API no indica filtro por fecha
            'expense-categories',
        ]
        
        # --- ENTIDADES CON FILTRO INCREMENTAL ---
        # Solo las que estamos 100% seguros de que la API de Fudo soporta el filtro filter[createdAt]
        self.incremental_filter_entities_by_field = {
            'expenses': 'createdAt',
        }

    def set_auth_token(self, token: str):
        self.auth_token = token
        logger.debug("Token de autenticación establecido para FudoApiClient.")

    def get_data(self, entity_name: str, id_sucursal: str, last_extracted_ts: datetime = None) -> list[dict]:
        """
        Extrae datos paginados de la API de Fudo.
        Para entidades en 'entities_for_full_refresh', siempre realiza un Full Refresh.
        Para otras, usa extracción incremental/completa genérica.
        """
        if not self.auth_token:
            raise ValueError("Token de autenticación no establecido. Llama a set_auth_token primero.")

        request_url = f"{self.api_base_url}/v1alpha1/{entity_name}"
        page_size = 500
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json"
        }

        # --- Lógica para entidades de Full Refresh ---
        if entity_name in self.entities_for_full_refresh:
            logger.info(f"\n--- Iniciando extracción de '{entity_name}' para sucursal '{id_sucursal}' con ESTRATEGIA DE REFRESH COMPLETO. ---")
            
            all_items = self._get_paginated_data_generic(
                request_url=request_url,
                headers=headers,
                page_size=page_size,
                entity_name=entity_name,
                id_sucursal=id_sucursal,
                apply_incremental_filter=False, # ¡NO APLICAR FILTRO DE FECHA!
                start_page=1,
                max_pages=-1, # <--- ⚠️ ATENCIÓN: PUESTO EN 1 PARA TU PRUEBA RÁPIDA. CAMBIAR A -1 PARA PRODUCCIÓN ⚠️
                filter_params=None,
                fields_key=self.fields_key_mapping.get(entity_name),
                fields_params=self.fields_parameters.get(self.fields_key_mapping.get(entity_name))
            )
            logger.info(f"  Total de '{entity_name}' extraídas (carga completa): {len(all_items)}")
            return all_items
            
        else:
            # --- Lógica genérica para otras entidades (incremental si aplica) ---
            logger.info(f"  Iniciando extracción de '{entity_name}' para sucursal '{id_sucursal}' con estrategia incremental/full.")
            
            # Determinar qué campo de filtro incremental usar
            incremental_field = self.incremental_filter_entities_by_field.get(entity_name)
            
            return self._get_paginated_data_generic(
                request_url=request_url,
                headers=headers,
                page_size=page_size,
                entity_name=entity_name,
                id_sucursal=id_sucursal,
                apply_incremental_filter=bool(last_extracted_ts) and bool(incremental_field),
                incremental_filter_field=incremental_field,
                incremental_filter_ts=last_extracted_ts,
                fields_key=self.fields_key_mapping.get(entity_name),
                fields_params=self.fields_parameters.get(self.fields_key_mapping.get(entity_name)),
                start_page=1,
                max_pages=-1 # <--- ⚠️ ATENCIÓN: PUESTO EN 1 PARA TU PRUEBA RÁPIDA. CAMBIAR A -1 PARA PRODUCCIÓN ⚠️
            )

    # --- MÉTODO AUXILIAR que encapsula la lógica de paginación y reintentos ---
    def _get_paginated_data_generic(self, request_url: str, headers: dict, page_size: int,
                                    entity_name: str, id_sucursal: str,
                                    apply_incremental_filter: bool, incremental_filter_field: str = 'createdAt',
                                    incremental_filter_ts: datetime = None,
                                    fields_key: str = None, fields_params: str = None,
                                    start_page: int = 1, max_pages: int = -1,
                                    filter_params: dict = None) -> list[dict]:
        all_items =[]
        current_page = start_page
        
        params = {}
        # Aplicar filtros adicionales si se proporcionaron
        if filter_params:
            params.update(filter_params)

        # Aplicar filtro incremental si se solicita
        if apply_incremental_filter and incremental_filter_ts:
            formatted_ts = incremental_filter_ts.astimezone(timezone.utc).isoformat(timespec='seconds')
            if not formatted_ts.endswith('Z'):
                formatted_ts += 'Z'
            params[f'filter[{incremental_filter_field}]'] = f"gte.{formatted_ts}"
            logger.debug(f"  Aplicando filtro incremental '{incremental_filter_field} >= {formatted_ts}' para {entity_name}.")
        
        # Aplicar parámetros 'fields' si se solicitan
        if fields_key and fields_params:
            params[f'fields[{fields_key}]'] = fields_params
            logger.debug(f"  Aplicando parámetro 'fields[{fields_key}]' para '{entity_name}'.")

        while True:
            if max_pages != -1 and current_page > (start_page - 1) + max_pages:
                logger.debug(f"  Alcanzado el límite de {max_pages} páginas para '{entity_name}'.")
                break
            
            retries = 0
            delay = self.initial_backoff_delay

            while retries < self.max_retries:
                try:
                    current_params = params.copy()
                    current_params['page[size]'] = page_size
                    current_params['page[number]'] = current_page

                    logger.debug(f"GET {request_url} params={current_params} (Intento {retries+1}/{self.max_retries}, pág {current_page})")
                    response = requests.get(request_url, params=current_params, headers=headers, timeout=60)
                    response.raise_for_status()

                    data = response.json().get('data',[])
                    logger.debug(f"Página {current_page}: {len(data)} ítems recuperados para '{entity_name}' ({id_sucursal}).")

                    all_items.extend(data)

                    if not data or len(data) < page_size:
                        logger.debug(f"  Última página o página incompleta. Extracción de '{entity_name}' finalizada.")
                        return all_items

                    current_page += 1
                    time.sleep(self.inter_page_delay)
                    break

                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code
                    if status in[429, 500, 502, 503, 504]:
                        retries += 1
                        logger.warning(f"HTTP {status} en '{entity_name}' (pág {current_page}). Reintentando en {delay}s ({retries}/{self.max_retries})...")
                        time.sleep(delay)
                        delay = min(delay * 2, self.max_backoff_delay)
                    elif status == 401:
                        logger.error("Token expirado o inválido (401). No reintentar.")
                        raise
                    elif status == 400:
                        logger.error(f"Error 400: parámetro 'fields' o filtro inválido para '{entity_name}'. {e.response.text}", exc_info=True)
                        raise
                    else:
                        logger.error(f"HTTP {status} no reintentable en '{entity_name}' (pág {current_page}): {e.response.text}", exc_info=True)
                        raise

                except requests.exceptions.RequestException as e:
                    retries += 1
                    logger.warning(f"Error de conexión en '{entity_name}' (pág {current_page}). Reintentando en {delay}s ({retries}/{self.max_retries})... {e}")
                    time.sleep(delay)
                    delay = min(delay * 2, self.max_backoff_delay)

            else:
                logger.error(f"Máximo de reintentos ({self.max_retries}) alcanzado para '{entity_name}' ({id_sucursal}) en la pág {current_page}.")
                raise ConnectionError(f"Fallo al extraer '{entity_name}' tras {self.max_retries} reintentos.")
        
        return all_items