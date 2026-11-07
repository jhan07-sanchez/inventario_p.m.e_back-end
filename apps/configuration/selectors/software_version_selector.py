import re
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q, QuerySet

from apps.configuration.models import SoftwareVersion, UserVersionRead
from apps.core.selectors.base_selector import BaseSelector


class SoftwareVersionSelector(BaseSelector[SoftwareVersion]):
    """
    Selector para consultas de lectura sobre versiones de software.
    Centraliza el acceso a la base de datos, resolución de SemVer y caché.
    """

    CACHE_KEY_LATEST = "sw_version_latest_published"
    CACHE_KEY_UPDATE_CHECK = "sw_version_update_check"
    CACHE_TIMEOUT = 300  # 5 minutos

    def __init__(self):
        super().__init__(SoftwareVersion)

    def get_queryset(self, include_deleted: bool = False) -> QuerySet[SoftwareVersion]:
        qs = super().get_queryset(include_deleted=include_deleted)
        return (
            qs.select_related("created_by", "published_by")
            .prefetch_related("changelog_entries")
            .annotate(
                total_changes=Count(
                    "changelog_entries",
                    filter=Q(changelog_entries__is_active=True),
                )
            )
        )

    @staticmethod
    def get_installed_version() -> str:
        """
        Retorna la versión instalada actualmente en el backend.
        La fuente de verdad es la constante de configuración del despliegue.
        """
        return getattr(settings, "APP_VERSION", "1.0.0")

    @staticmethod
    def parse_semver(version_str: str) -> tuple[int, int, int]:
        """
        Parsea un string SemVer (MAJOR.MINOR.PATCH) a una tupla de enteros.
        Si no es válido, retorna (0, 0, 0).
        """
        if not version_str:
            return (0, 0, 0)
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version_str.strip())
        if not match:
            return (0, 0, 0)
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    @classmethod
    def is_newer_version(cls, version_a: str, version_b: str) -> bool:
        """
        Determina si version_a es estrictamente mayor que version_b según SemVer.
        """
        return cls.parse_semver(version_a) > cls.parse_semver(version_b)

    @classmethod
    def get_latest_published_version(cls) -> Optional[SoftwareVersion]:
        """
        Obtiene la última versión publicada con soporte de caché.
        """
        cached = cache.get(cls.CACHE_KEY_LATEST)
        if cached is not None:
            return cached

        published_versions = (
            SoftwareVersion.objects.filter(status=SoftwareVersion.Status.PUBLISHED)
            .select_related("created_by", "published_by")
            .prefetch_related("changelog_entries")
            .order_by("-published_at", "-id_version")
        )

        # Encontrar la versión de mayor SemVer entre las publicadas
        latest = None
        for v in published_versions:
            if latest is None or cls.is_newer_version(v.version, latest.version):
                latest = v

        if latest:
            cache.set(cls.CACHE_KEY_LATEST, latest, timeout=cls.CACHE_TIMEOUT)

        return latest

    @classmethod
    def check_for_updates(cls) -> dict:
        """
        Compara la versión instalada con la última versión publicada
        y determina si existe una actualización disponible.
        """
        cached_result = cache.get(cls.CACHE_KEY_UPDATE_CHECK)
        if cached_result is not None:
            return cached_result

        installed = cls.get_installed_version()
        latest = cls.get_latest_published_version()

        has_update = False
        is_mandatory = False
        priority = SoftwareVersion.Priority.OPTIONAL
        latest_data = None

        # 1. SIEMPRE preparamos la data de la última versión (exista o no actualización)
        if latest:
            entries_by_cat = {}
            for entry in latest.changelog_entries.all():
                cat = entry.category
                if cat not in entries_by_cat:
                    entries_by_cat[cat] = []
                entries_by_cat[cat].append({
                    "id": entry.id_entry,
                    "title": entry.title,
                    "description": entry.description,
                    "order": entry.order,
                })

            latest_data = {
                "id": latest.id_version,
                "version": latest.version,
                "name": latest.name,
                "priority": latest.priority,
                "priority_display": latest.get_priority_display(),
                "published_at": latest.published_at.isoformat() if latest.published_at else None,
                "description": latest.description,
                "min_compatible_version": latest.min_compatible_version,
                "prerequisites": latest.prerequisites,
                "upgrade_instructions": latest.upgrade_instructions,
                "changelog": entries_by_cat,
                "total_changes": getattr(latest, "total_changes", latest.changelog_entries.count()),
            }

            # 2. Evaluamos si esa versión es más nueva que la instalada
            if cls.is_newer_version(latest.version, installed):
                has_update = True
                priority = latest.priority
                is_mandatory = (latest.priority == SoftwareVersion.Priority.MANDATORY)

        installed_record = SoftwareVersion.objects.filter(
            version=installed, status=SoftwareVersion.Status.PUBLISHED
        ).first()

        result = {
            "installed_version": installed,
            "installed_version_published_at": (
                installed_record.published_at.isoformat()
                if installed_record and installed_record.published_at
                else None
            ),
            "has_update": has_update,
            "latest_version": latest.version if latest else installed,
            "is_mandatory": is_mandatory,
            "priority": priority,
            "latest_release": latest_data, # <-- Ahora SIEMPRE vendrá lleno si hay versiones
        }

        cache.set(cls.CACHE_KEY_UPDATE_CHECK, result, timeout=cls.CACHE_TIMEOUT)
        return result
    @classmethod
    def get_user_notifications(cls, user, limit: int = 15) -> dict:
        """
        Retorna las notificaciones de versiones publicadas para un usuario específico,
        indicando cuáles han sido leídas y cuáles están pendientes.
        """
        if not user or not user.is_authenticated:
            return {"unread_count": 0, "notifications": []}

        published_qs = (
            SoftwareVersion.objects.filter(status=SoftwareVersion.Status.PUBLISHED, is_active=True)
            .select_related("published_by")
            .annotate(
                total_changes=Count(
                    "changelog_entries", filter=Q(changelog_entries__is_active=True)
                )
            )
            .order_by("-published_at", "-id_version")
        )

        read_records = {
            r.version_id: r.read_at
            for r in UserVersionRead.objects.filter(user=user)
        }

        notifications = []
        for ver in published_qs[:limit]:
            is_read = ver.id_version in read_records
            notifications.append(
                {
                    "id": ver.id_version,
                    "version": ver.version,
                    "title": f"Versión v{ver.version} disponible" if not ver.name else f"v{ver.version} - {ver.name}",
                    "name": ver.name,
                    "description": ver.description,
                    "priority": ver.priority,
                    "priority_display": ver.get_priority_display(),
                    "published_at": ver.published_at.isoformat() if ver.published_at else None,
                    "total_changes": getattr(ver, "total_changes", 0),
                    "is_read": is_read,
                    "read_at": read_records[ver.id_version].isoformat() if is_read else None,
                }
            )

        total_published = published_qs.count()
        total_read = len(read_records)
        total_unread = max(0, total_published - total_read)

        return {
            "unread_count": total_unread,
            "notifications": notifications,
        }

    @classmethod
    def get_user_unread_count(cls, user) -> int:
        """
        Calcula de forma eficiente el conteo de notificaciones no leídas de un usuario.
        """
        if not user or not user.is_authenticated:
            return 0
        total_published = SoftwareVersion.objects.filter(
            status=SoftwareVersion.Status.PUBLISHED, is_active=True
        ).count()
        user_read_count = UserVersionRead.objects.filter(
            user=user,
            version__status=SoftwareVersion.Status.PUBLISHED,
            version__is_active=True,
        ).count()
        return max(0, total_published - user_read_count)

    @classmethod
    def get_published_history(cls) -> QuerySet[SoftwareVersion]:
        """
        Retorna el historial completo de versiones publicadas.
        Accesible por cualquier usuario autenticado o para documentación.
        """
        return (
            SoftwareVersion.objects.filter(status=SoftwareVersion.Status.PUBLISHED)
            .select_related("created_by", "published_by")
            .prefetch_related("changelog_entries")
            .order_by("-published_at", "-id_version")
        )

    @classmethod
    def get_version_by_id(
        cls, version_id: int, include_deleted: bool = False
    ) -> Optional[SoftwareVersion]:
        """
        Obtiene el detalle completo de una versión por su ID.
        """
        qs = cls().get_queryset(include_deleted=include_deleted)
        return qs.filter(pk=version_id).first()

    @classmethod
    def get_version_by_number(
        cls, version_str: str, include_deleted: bool = False
    ) -> Optional[SoftwareVersion]:
        """
        Obtiene el detalle completo de una versión por su número SemVer.
        """
        qs = cls().get_queryset(include_deleted=include_deleted)
        return qs.filter(version=version_str.strip()).first()
