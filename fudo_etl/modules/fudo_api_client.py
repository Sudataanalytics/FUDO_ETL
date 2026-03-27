# fudo_etl/modules/fudo_api_client.py
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
        
        # --- Mapeo EXPLÍCITO: SOLO para entidades que requieren fields para traer atributos ---
        self.fields_key_mapping = {
            'expenses': 'expense',
            'expense-categories': 'expenseCategory',
            'providers': 'provider',
            'products': 'product',
        }

        self.fields_parameters = {
            'expense': 'amount,canceled,cashRegister,createdAt,date,description,dueDate,expenseCategory,expenseItems,paymentDate,paymentMethod,provider,receiptNumber,receiptType,status,useInCashCount,user',
            'expenseCategory': 'active,financialCategory,name,parentCategory',
            'provider': 'name,email,address,phone,comment,active,internal,providerHouseAccountBalance,fiscalNumber',
            'product': 'active,code,cost,description,enableOnlineMenu,enableQrMenu,favourite,imageUrl,name,position,price,sellAlone,stock,stockControl',
        }

        # --- Entidades que siempre se descargan completas (Sin filtro de fecha) ---
        self.entities_for_full_refresh = [
            'sales', 'payments', 'payment-methods', 'product-categories', 
            'product-modifiers', 'products', 'customers', 'discounts', 
            'ingredients', 'items', 'kitchens', 'roles', 'rooms', 
            'tables', 'users', 'providers', 'expense-categories'
        ]

        # --- Entidades que soportan filtro incremental ---
        self.incremental_filter_entities = {
            'expenses': 'createdAt',
        }

    def set_auth_token(self, token: str):
        self.auth_token = token
        logger.debug("Token de autenticación establecido.")

    def get_data(self, entity_name: str, id_sucursal: str, last_extracted_ts: datetime = None) -> list[dict]:
        request_url = f"{self.api_base_url}/v1alpha1/{entity_name}"
        page_size = 500
        headers = {"Authorization": f"Bearer {self.auth_token}", "Accept": "application/json"}

        # Decidir si es Full Refresh o Incremental
        is_full_refresh = entity_name in self.entities_for_full_refresh
        
        if is_full_refresh:
            logger.info(f"--- ESTRATEGIA FULL REFRESH: {entity_name} ---")
        else:
            logger.info(f"--- ESTRATEGIA INCREMENTAL: {entity_name} ---")

        return self._get_paginated_data_generic(
            request_url=request_url,
            headers=headers,
            page_size=page_size,
            entity_name=entity_name,
            id_sucursal=id_sucursal,
            apply_incremental_filter=(not is_full_refresh and last_extracted_ts is not None),
            incremental_filter_ts=last_extracted_ts,
            fields_key=self.fields_key_mapping.get(entity_name),
            fields_params=self.fields_parameters.get(self.fields_key_mapping.get(entity_name, '')),
            max_pages=-1 # <--- CAMBIAR A -1 PARA PRODUCCIÓN
        )

    def _get_paginated_data_generic(self, request_url, headers, page_size, entity_name, id_sucursal, 
                                    apply_incremental_filter, incremental_filter_ts=None, 
                                    fields_key=None, fields_params=None, start_page=1, max_pages=-1):
        all_items = []
        current_page = start_page
        params = {}

        if apply_incremental_filter and incremental_filter_ts:
            filter_field = self.incremental_filter_entities.get(entity_name, 'createdAt')
            formatted_ts = incremental_filter_ts.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
            params[f'filter[{filter_field}]'] = f"gte.{formatted_ts}"
        
        if fields_key and fields_params:
            params[f'fields[{fields_key}]'] = fields_params

        while True:
            if max_pages != -1 and current_page > (start_page - 1) + max_pages: break
            
            retries = 0
            delay = self.initial_backoff_delay
            while retries < self.max_retries:
                try:
                    current_params = params.copy()
                    current_params['page[size]'] = page_size
                    current_params['page[number]'] = current_page
                    response = requests.get(request_url, params=current_params, headers=headers, timeout=60)
                    response.raise_for_status()
                    data = response.json().get('data', [])
                    all_items.extend(data)
                    if not data or len(data) < page_size: return all_items
                    current_page += 1
                    time.sleep(self.inter_page_delay)
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [429, 500, 502, 503, 504]:
                        retries += 1
                        time.sleep(delay)
                        delay = min(delay * 2, self.max_backoff_delay)
                    else:
                        logger.error(f"Error {e.response.status_code} en {entity_name}: {e.response.text}")
                        raise e
                except Exception:
                    retries += 1
                    time.sleep(delay)
            else: raise ConnectionError(f"Max retries for {entity_name}")
        return all_items