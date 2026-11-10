"""
Contexto de ejecución para Multi-Tenancy.
Utiliza contextvars para almacenar de forma segura y aislada (thread-safe y async-safe)
el identificador de la empresa activa durante el ciclo de vida de la petición HTTP.
"""

import contextvars
from typing import Optional

_current_company_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_company_id", default=None
)


def get_current_company_id() -> Optional[int]:
    """Retorna el ID de la empresa activa en el contexto actual, o None si no hay."""
    return _current_company_id.get()


def set_current_company_id(company_id: Optional[int]) -> contextvars.Token:
    """Establece el ID de la empresa activa en el contexto actual."""
    return _current_company_id.set(company_id)


def reset_current_company_id(token: contextvars.Token) -> None:
    """Restaura el contexto de la empresa anterior al token dado."""
    _current_company_id.reset(token)

