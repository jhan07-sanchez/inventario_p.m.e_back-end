from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SoftwareVersionCreateDto:
    """DTO para crear una nueva versión de software."""

    version: str
    name: str = ""
    description: str = ""
    priority: str = "RECOMMENDED"
    min_compatible_version: str = ""
    prerequisites: str = ""
    upgrade_instructions: str = ""
    changelog_entries: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class SoftwareVersionUpdateDto:
    """DTO para actualizar una versión de software en borrador."""

    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    min_compatible_version: Optional[str] = None
    prerequisites: Optional[str] = None
    upgrade_instructions: Optional[str] = None


@dataclass(frozen=True)
class ChangelogEntryDto:
    """DTO para una entrada de changelog."""

    category: str
    title: str
    description: str = ""
    order: int = 0

