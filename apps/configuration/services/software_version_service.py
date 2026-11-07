from typing import TYPE_CHECKING, Optional

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.configuration.dto import (
    ChangelogEntryDto,
    SoftwareVersionCreateDto,
    SoftwareVersionUpdateDto,
)
from apps.configuration.models import (
    ConfigurationAudit,
    SoftwareVersion,
    UserVersionRead,
    VersionChangelogEntry,
)
from apps.configuration.selectors.software_version_selector import (
    SoftwareVersionSelector,
)
from apps.core.exceptions.custom_exceptions import (
    SoftwareVersionAlreadyExistsException,
    SoftwareVersionAlreadyPublishedException,
    SoftwareVersionCannotWithdrawException,
    SoftwareVersionDowngradeException,
    SoftwareVersionInvalidSemverException,
)
from apps.core.services.base_service import BaseService

if TYPE_CHECKING:
    from apps.users.models import User


class SoftwareVersionService(BaseService[SoftwareVersion]):
    """
    Servicio encargado de la lógica de negocio, validaciones y ciclo de vida
    de las versiones de software del ERP.
    Garantiza atomicidad, auditoría, consistencia de SemVer y gestión de caché.
    """

    def __init__(self):
        super().__init__(SoftwareVersion)

    @staticmethod
    def invalidate_cache() -> None:
        """
        Invalida las llaves de caché asociadas a versiones y chequeos de actualización.
        """
        cache.delete(SoftwareVersionSelector.CACHE_KEY_LATEST)
        cache.delete(SoftwareVersionSelector.CACHE_KEY_UPDATE_CHECK)

    @classmethod
    @transaction.atomic
    def create_version(
        cls, dto: SoftwareVersionCreateDto, user: Optional["User"] = None
    ) -> SoftwareVersion:
        """
        Registra una nueva versión en estado BORRADOR (DRAFT).
        Valida que el SemVer sea válido y que no exista previamente.
        """
        v_str = dto.version.strip()
        if not SoftwareVersion.SEMVER_REGEX.match(v_str):
            raise SoftwareVersionInvalidSemverException()

        if SoftwareVersion.objects.filter(version=v_str).exists():
            raise SoftwareVersionAlreadyExistsException()

        version = SoftwareVersion.objects.create(
            version=v_str,
            name=dto.name.strip(),
            description=dto.description.strip(),
            priority=dto.priority,
            min_compatible_version=dto.min_compatible_version.strip(),
            prerequisites=dto.prerequisites.strip(),
            upgrade_instructions=dto.upgrade_instructions.strip(),
            status=SoftwareVersion.Status.DRAFT,
            created_by=user,
        )

        # Crear entradas de changelog iniciales si fueron enviadas
        for idx, entry_data in enumerate(dto.changelog_entries):
            category = entry_data.get("category", VersionChangelogEntry.Category.FEATURE)
            title = entry_data.get("title", "").strip()
            desc = entry_data.get("description", "").strip()
            order = entry_data.get("order", idx)
            if title:
                VersionChangelogEntry.objects.create(
                    version=version,
                    category=category,
                    title=title,
                    description=desc,
                    order=order,
                )

        # Auditoría de creación
        ConfigurationAudit.objects.create(
            parameter=None,
            parameter_key=f"VERSION_{v_str}",
            action=ConfigurationAudit.Action.CREATE,
            user=user,
            old_value=None,
            new_value=f"Borrador v{v_str}",
            reason=f"Registro de borrador de versión {v_str}.",
        )

        cls.invalidate_cache()
        return version

    @classmethod
    @transaction.atomic
    def update_version(
        cls,
        version: SoftwareVersion,
        dto: SoftwareVersionUpdateDto,
        user: Optional["User"] = None,
    ) -> SoftwareVersion:
        """
        Actualiza los metadatos de una versión no publicada (DRAFT).
        Una versión publicada no puede modificarse silenciosamente.
        """
        if version.status == SoftwareVersion.Status.PUBLISHED:
            raise SoftwareVersionAlreadyPublishedException()

        update_fields = ["updated_at"]

        if dto.name is not None and dto.name != version.name:
            version.name = dto.name.strip()
            update_fields.append("name")

        if dto.description is not None and dto.description != version.description:
            version.description = dto.description.strip()
            update_fields.append("description")

        if dto.priority is not None and dto.priority != version.priority:
            version.priority = dto.priority
            update_fields.append("priority")

        if (
            dto.min_compatible_version is not None
            and dto.min_compatible_version != version.min_compatible_version
        ):
            version.min_compatible_version = dto.min_compatible_version.strip()
            update_fields.append("min_compatible_version")

        if (
            dto.prerequisites is not None
            and dto.prerequisites != version.prerequisites
        ):
            version.prerequisites = dto.prerequisites.strip()
            update_fields.append("prerequisites")

        if (
            dto.upgrade_instructions is not None
            and dto.upgrade_instructions != version.upgrade_instructions
        ):
            version.upgrade_instructions = dto.upgrade_instructions.strip()
            update_fields.append("upgrade_instructions")

        if len(update_fields) > 1:
            version.save(update_fields=update_fields)

            ConfigurationAudit.objects.create(
                parameter=None,
                parameter_key=f"VERSION_{version.version}",
                action=ConfigurationAudit.Action.UPDATE,
                user=user,
                old_value="DRAFT",
                new_value="DRAFT_UPDATED",
                reason=f"Actualización de metadatos de versión {version.version}.",
            )

        cls.invalidate_cache()
        return version

    @classmethod
    @transaction.atomic
    def add_changelog_entry(
        cls,
        version: SoftwareVersion,
        dto: ChangelogEntryDto,
        user: Optional["User"] = None,
    ) -> VersionChangelogEntry:
        """
        Agrega una nueva entrada de changelog a una versión.
        Si la versión ya está publicada, solo se audita el cambio.
        """
        entry = VersionChangelogEntry.objects.create(
            version=version,
            category=dto.category,
            title=dto.title.strip(),
            description=dto.description.strip(),
            order=dto.order,
        )

        cls.invalidate_cache()
        return entry

    @classmethod
    @transaction.atomic
    def delete_changelog_entry(
        cls, entry_id: int, user: Optional["User"] = None
    ) -> None:
        """
        Elimina una entrada de changelog específica.
        """
        entry = VersionChangelogEntry.objects.filter(pk=entry_id).first()
        if entry:
            version = entry.version
            if version.status == SoftwareVersion.Status.PUBLISHED:
                raise SoftwareVersionAlreadyPublishedException()
            entry.hard_delete()
            cls.invalidate_cache()

    @classmethod
    @transaction.atomic
    def publish_version(
        cls,
        version: SoftwareVersion,
        user: Optional["User"] = None,
        force: bool = False,
        force_reason: str = "",
    ) -> SoftwareVersion:
        """
        Publica una versión.
        Reglas de negocio:
        - Si ya está publicada, rechaza la operación.
        - Valida que la versión sea estrictamente superior a la última publicada,
          a menos que se proporcione force=True y force_reason justificado.
        - Registra fecha y usuario de publicación.
        - Invalida la caché de chequeo de versiones.
        """
        if version.status == SoftwareVersion.Status.PUBLISHED:
            raise SoftwareVersionAlreadyPublishedException()

        latest = SoftwareVersionSelector.get_latest_published_version()
        if latest and not force:
            if not SoftwareVersionSelector.is_newer_version(version.version, latest.version):
                raise SoftwareVersionDowngradeException(
                    f"No es posible publicar la versión {version.version} porque no es "
                    f"superior a la última versión publicada ({latest.version})."
                )

        version.status = SoftwareVersion.Status.PUBLISHED
        version.published_at = timezone.now()
        version.published_by = user
        version.save(update_fields=["status", "published_at", "published_by", "updated_at"])

        audit_reason = f"Publicación de versión {version.version}."
        if force:
            audit_reason += f" [FORZADO]: {force_reason}"

        ConfigurationAudit.objects.create(
            parameter=None,
            parameter_key=f"VERSION_{version.version}",
            action=ConfigurationAudit.Action.UPDATE,
            user=user,
            old_value="DRAFT",
            new_value="PUBLISHED",
            reason=audit_reason,
        )

        cls.invalidate_cache()
        return version

    @classmethod
    @transaction.atomic
    def withdraw_version(
        cls,
        version: SoftwareVersion,
        user: Optional["User"] = None,
        reason: str = "",
    ) -> SoftwareVersion:
        """
        Retira o despublica una versión del mercado/notificaciones.
        Solo permitido para versiones previamente publicadas.
        """
        if version.status != SoftwareVersion.Status.PUBLISHED:
            raise SoftwareVersionCannotWithdrawException()

        version.status = SoftwareVersion.Status.WITHDRAWN
        version.save(update_fields=["status", "updated_at"])

        ConfigurationAudit.objects.create(
            parameter=None,
            parameter_key=f"VERSION_{version.version}",
            action=ConfigurationAudit.Action.UPDATE,
            user=user,
            old_value="PUBLISHED",
            new_value="WITHDRAWN",
            reason=f"Retiro de versión {version.version}: {reason}",
        )

        cls.invalidate_cache()
        return version

    @classmethod
    @transaction.atomic
    def delete_draft(
        cls, version: SoftwareVersion, user: Optional["User"] = None
    ) -> None:
        """
        Elimina una versión que se encuentra en borrador.
        No se permite eliminar directamente versiones publicadas.
        """
        if version.status == SoftwareVersion.Status.PUBLISHED:
            raise SoftwareVersionAlreadyPublishedException(
                "No se puede eliminar una versión publicada. Utilice la opción de retirar versión."
            )

        v_num = version.version
        version.delete()

        ConfigurationAudit.objects.create(
            parameter=None,
            parameter_key=f"VERSION_{v_num}",
            action=ConfigurationAudit.Action.DEACTIVATE,
            user=user,
            old_value=version.status,
            new_value=None,
            reason=f"Eliminación de borrador de versión {v_num}.",
        )

        cls.invalidate_cache()

    @classmethod
    @transaction.atomic
    def mark_version_as_read(
        cls, version: SoftwareVersion, user: "User"
    ) -> UserVersionRead:
        """
        Marca una versión como leída/consultada por el usuario especificado.
        Garantiza que la notificación no vuelva a marcarse como pendiente.
        """
        read_obj, _ = UserVersionRead.objects.get_or_create(
            user=user,
            version=version,
        )
        return read_obj

    @classmethod
    @transaction.atomic
    def mark_all_versions_as_read(cls, user: "User") -> int:
        """
        Marca todas las versiones publicadas como leídas para el usuario.
        Retorna la cantidad de versiones que fueron marcadas como leídas.
        """
        published_versions = SoftwareVersion.objects.filter(
            status=SoftwareVersion.Status.PUBLISHED, is_active=True
        )
        already_read_ids = set(
            UserVersionRead.objects.filter(user=user).values_list("version_id", flat=True)
        )

        to_create = [
            UserVersionRead(user=user, version=v)
            for v in published_versions
            if v.id_version not in already_read_ids
        ]

        if to_create:
            UserVersionRead.objects.bulk_create(to_create, ignore_conflicts=True)

        return len(to_create)

