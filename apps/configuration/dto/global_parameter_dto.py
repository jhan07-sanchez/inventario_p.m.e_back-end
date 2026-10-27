from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class GlobalParameterCreateDto:
    """
    DTO para la creación de un parámetro global.
    """

    key: str
    value: str
    data_type: str
    description: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GlobalParameterUpdateDto:
    """
    DTO para la actualización de un parámetro global.
    """

    value: Optional[str] = None
    data_type: Optional[str] = None
    description: Optional[str] = None
