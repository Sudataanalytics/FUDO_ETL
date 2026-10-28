# fudo_etl/modules/http_retry.py
import os
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import MaxRetryError
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = [429, 500, 502, 503, 504]


class CappedRetry(Retry):
    """
    Retry que respeta Retry-After pero con un tope, para que un header enorme
    (ej. Retry-After: 3600) no deje el proceso dormido sin control.
    El tope cubre la ventana de rate limit de Fudo (~5 min): si fuera menor, se reintentaría
    antes de que la ventana se libere y se gastarían los reintentos en 429 seguidos.
    """
    max_retry_after = float(os.getenv("FUDO_MAX_RETRY_AFTER_SECONDS", "300"))

    def get_retry_after(self, response):
        retry_after = super().get_retry_after(response)
        if retry_after is None:
            return None
        return min(retry_after, self.max_retry_after)

    def increment(self, method=None, url=None, response=None, error=None, _pool=None, _stacktrace=None):
        """Igual que Retry.increment, pero deja en el log cada reintento y cuánto se va a esperar."""
        if response is not None:
            cause = f"HTTP {response.status}"
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header is not None:
                cause += f" (Retry-After: {retry_after_header})"
        else:
            cause = type(error).__name__ if error else "error desconocido"
        try:
            new_retry = super().increment(method, url, response, error, _pool, _stacktrace)
        except MaxRetryError:
            logger.error(f"{method} {url}: {cause}. Reintentos agotados.")
            raise

        wait = self.get_retry_after(response) if response is not None else None
        if wait is None:
            wait = new_retry.get_backoff_time()
        max_attempts = len(self.history) + self.total
        logger.warning(f"{method} {url}: {cause}. Reintento {len(new_retry.history)}/{max_attempts} en {wait:.0f}s.")
        return new_retry


def build_retry_session(methods: set[str], total: int = 5) -> requests.Session:
    """
    Session de requests con reintentos solo ante errores transitorios
    (429/5xx y errores de conexión/lectura). Los 4xx restantes fallan de inmediato.
    """
    retry = CappedRetry(
        total=total,
        connect=total,
        read=total,
        status=total,
        other=0,
        backoff_factor=2,
        backoff_max=60,
        status_forcelist=TRANSIENT_STATUS_CODES,
        allowed_methods=frozenset(methods),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update({"Accept": "application/json"})
    return session
