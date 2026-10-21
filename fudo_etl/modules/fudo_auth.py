# fudo-etl-project/fudo_auth.py
import os
import requests
import json
import logging
import threading
from datetime import datetime, timedelta, timezone

from .db_manager import DBManager
from .etl_metadata_manager import ETLMetadataManager
from .get_secret import get_secret
from .http_retry import build_retry_session

logger = logging.getLogger(__name__)

class FudoAuthenticator:
    def __init__(self, db_manager: DBManager, auth_endpoint: str, project_id: str):
        self.db_manager = db_manager
        self.auth_endpoint = auth_endpoint
        self.project_id = project_id
        self.metadata_manager = ETLMetadataManager(db_manager) # Usa el metadata manager aquí
        # Pedir un token nuevo es seguro de repetir, así que el POST también se reintenta ante fallas transitorias
        self.session = build_retry_session({"POST"}, total=3)
        # Vigencia mínima para reusar un token guardado: debe cubrir lo que dura la extracción de una sucursal
        self.min_token_validity = timedelta(minutes=int(os.getenv("FUDO_TOKEN_MIN_VALIDITY_MINUTES", "60")))
        # Varios hilos pueden pedir/renovar tokens a la vez; se serializa (es poco frecuente)
        # para no compartir la Session entre hilos ni pisar el token guardado en la base.
        self._lock = threading.Lock()

    def _get_credentials_from_secret_source(self, secret_api_key_name: str, secret_api_secret_name: str) -> tuple[str, str]:
        """Obtiene apiKey y apiSecret de Secret Manager (o ENV local)."""
        api_key = get_secret(secret_api_key_name, self.project_id)
        api_secret = get_secret(secret_api_secret_name, self.project_id)
        return api_key, api_secret

    def _request_new_token(self, api_key: str, api_secret: str) -> dict:
        """Solicita un nuevo token a la API de autenticación de Fudo."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = json.dumps({"apiKey": api_key, "apiSecret": api_secret})
        
        try:
            logger.info(f"Realizando POST a {self.auth_endpoint} para obtener nuevo token...")
            response = self.session.post(self.auth_endpoint, headers=headers, data=payload, timeout=(5, 15))
            response.raise_for_status() # Lanza un error para códigos de respuesta 4xx/5xx
            response_json = response.json()
            logger.info("Nuevo token obtenido de Fudo API Auth.")
            return response_json
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al solicitar nuevo token: {e}", exc_info=True)
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Fudo API Auth Response: {e.response.status_code} - {e.response.text}")
            raise ConnectionError(f"Fudo API Auth Error: {e}")

    def get_valid_token(self, id_sucursal: str, secret_api_key_name: str, secret_api_secret_name: str,
                        force_refresh: bool = False) -> str:
        """
        Obtiene un token válido para una sucursal.
        Si está expirado, cerca de expirar o force_refresh=True (ej. tras un 401), solicita uno nuevo y lo guarda.
        """
        with self._lock:
            return self._get_valid_token(id_sucursal, secret_api_key_name, secret_api_secret_name, force_refresh)

    def _get_valid_token(self, id_sucursal: str, secret_api_key_name: str, secret_api_secret_name: str,
                         force_refresh: bool) -> str:
        current_time_utc = datetime.now(timezone.utc)
        
        # 1. Intentar obtener token de la base de datos a través del metadata_manager
        db_token_data = None if force_refresh else self.metadata_manager.get_fudo_token_data(id_sucursal)

        access_token = None
        token_is_valid = False

        if db_token_data:
            db_access_token = db_token_data['access_token']
            db_expiration_utc = db_token_data['token_expiration_utc']
            
            # Considerar el token válido solo si le queda al menos la vigencia mínima configurada
            if db_expiration_utc and db_expiration_utc > (current_time_utc + self.min_token_validity):
                access_token = db_access_token
                token_is_valid = True
                logger.debug(f"Usando token cacheado para sucursal {id_sucursal}. Expira en {db_expiration_utc - current_time_utc}.")
            else:
                logger.warning(f"Token cacheado para sucursal {id_sucursal} expirado o próximo a expirar.")

        if not token_is_valid:
            logger.info(f"Solicitando nuevo token para sucursal {id_sucursal}.")
            try:
                api_key, api_secret = self._get_credentials_from_secret_source(secret_api_key_name, secret_api_secret_name)
                
                new_token_data = self._request_new_token(api_key, api_secret)
                access_token = new_token_data['token']
                
                # El 'exp' de Fudo es un timestamp de segundos desde Epoch
                token_expiration_utc = datetime.fromtimestamp(new_token_data['exp'], tz=timezone.utc)
                
                # Actualizar/insertar en la base de datos a través del metadata_manager
                self.metadata_manager.update_fudo_token_data(id_sucursal, access_token, token_expiration_utc)
                logger.info(f"Nuevo token obtenido y guardado para sucursal {id_sucursal}. Expira: {token_expiration_utc}")
            except Exception as e:
                logger.error(f"Fallo al obtener o guardar nuevo token para sucursal {id_sucursal}: {e}", exc_info=True)
                raise

        if not access_token:
            raise ValueError(f"No se pudo obtener un token válido para la sucursal {id_sucursal}.")

        return access_token


class BranchTokenProvider:
    """
    Token compartido por todos los hilos que extraen una misma sucursal.
    Si varios reciben un 401 a la vez, solo el primero renueva; el resto reutiliza el token nuevo.
    """

    def __init__(self, authenticator: FudoAuthenticator, id_sucursal: str,
                 secret_api_key_name: str, secret_api_secret_name: str):
        self.authenticator = authenticator
        self.id_sucursal = id_sucursal
        self.secret_api_key_name = secret_api_key_name
        self.secret_api_secret_name = secret_api_secret_name
        self._lock = threading.Lock()
        self.token = authenticator.get_valid_token(id_sucursal, secret_api_key_name, secret_api_secret_name)

    def refresh(self, stale_token: str) -> str:
        """Devuelve un token nuevo; si otro hilo ya renovó el que falló, devuelve ese sin pedir otro."""
        with self._lock:
            if self.token == stale_token:
                self.token = self.authenticator.get_valid_token(
                    self.id_sucursal, self.secret_api_key_name, self.secret_api_secret_name, force_refresh=True
                )
            return self.token