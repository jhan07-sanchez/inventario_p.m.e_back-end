import re

from django.conf import settings
from django.db import models

from apps.core.models.active_model import ActiveModel


class SoftwareVersion(ActiveModel):
    """
    Modelo para gestionar el ciclo de vida de las versiones del software.

    Cada registro representa una versión que puede estar en estado borrador
    o publicada. Los usuarios con permisos administrativos registran las
    novedades, correcciones y requisitos asociados a cada versión.

    La instalación real de la versión siempre es un procedimiento manual
    controlado por el administrador.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PUBLISHED = "PUBLISHED", "Publicada"
        WITHDRAWN = "WITHDRAWN", "Retirada"

    class Priority(models.TextChoices):
        MANDATORY = "MANDATORY", "Obligatoria"
        RECOMMENDED = "RECOMMENDED", "Recomendada"
        OPTIONAL = "OPTIONAL", "Opcional"

    # ── Identificación ──────────────────────────────────────
    id_version = models.BigAutoField(
        primary_key=True,
        verbose_name="ID Versión",
    )
    version = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de versión",
        help_text="Formato SemVer: MAJOR.MINOR.PATCH (ej. 1.2.0)",
    )
    name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Nombre de la versión",
        help_text="Nombre descriptivo opcional (ej. 'Aurora', 'Release Candidate').",
    )

    # ── Estado y publicación ────────────────────────────────
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Estado de publicación",
    )
    priority = models.CharField(
        max_length=12,
        choices=Priority.choices,
        default=Priority.RECOMMENDED,
        verbose_name="Prioridad de actualización",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de publicación",
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_versions",
        verbose_name="Publicado por",
    )

    # ── Descripción general ─────────────────────────────────
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción general",
    )

    # ── Requisitos y actualización ──────────────────────────
    min_compatible_version = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Versión mínima compatible",
        help_text="Versión mínima desde la cual se puede actualizar directamente.",
    )
    prerequisites = models.TextField(
        blank=True,
        default="",
        verbose_name="Requisitos previos",
        help_text="Pasos que deben completarse antes de la actualización.",
    )
    upgrade_instructions = models.TextField(
        blank=True,
        default="",
        verbose_name="Instrucciones de actualización",
        help_text="Procedimiento manual para instalar esta versión.",
    )

    # ── Auditoría de autoría ────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_versions",
        verbose_name="Creado por",
    )

    # ── SemVer regex ────────────────────────────────────────
    SEMVER_REGEX = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$"
    )

    class Meta:
        db_table = "software_versions"
        verbose_name = "Versión del Software"
        verbose_name_plural = "Versiones del Software"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="idx_version_status_pub"),
        ]

    def __str__(self) -> str:
        label = f"v{self.version}"
        if self.name:
            label += f" ({self.name})"
        return f"{label} — {self.get_status_display()}"

    def clean(self) -> None:
        """Valida el formato SemVer del número de versión."""
        from django.core.exceptions import ValidationError

        super().clean()
        if self.version and not self.SEMVER_REGEX.match(self.version):
            raise ValidationError(
                {
                    "version": (
                        f"El formato de versión '{self.version}' no es válido. "
                        "Utilice SemVer: MAJOR.MINOR.PATCH (ej. 1.2.0)."
                    )
                }
            )

    @property
    def semver_tuple(self) -> tuple[int, int, int]:
        """Devuelve la versión como tupla numérica para comparaciones."""
        match = self.SEMVER_REGEX.match(self.version or "0.0.0")
        if not match:
            return (0, 0, 0)
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


class VersionChangelogEntry(ActiveModel):
    """
    Entrada individual del changelog asociado a una versión.

    Clasifica cada cambio por categoría (nueva funcionalidad, mejora,
    corrección, seguridad, técnico, incompatible) para facilitar
    la presentación organizada al usuario.
    """

    class Category(models.TextChoices):
        FEATURE = "FEATURE", "Nueva funcionalidad"
        IMPROVEMENT = "IMPROVEMENT", "Mejora"
        BUGFIX = "BUGFIX", "Corrección de error"
        SECURITY = "SECURITY", "Seguridad"
        TECHNICAL = "TECHNICAL", "Cambio técnico"
        BREAKING = "BREAKING", "Cambio incompatible"

    id_entry = models.BigAutoField(
        primary_key=True,
        verbose_name="ID Entrada",
    )
    version = models.ForeignKey(
        SoftwareVersion,
        on_delete=models.CASCADE,
        related_name="changelog_entries",
        verbose_name="Versión",
    )
    category = models.CharField(
        max_length=12,
        choices=Category.choices,
        verbose_name="Categoría",
        db_index=True,
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Título",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción detallada",
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Orden de visualización",
    )

    class Meta:
        db_table = "version_changelog_entries"
        verbose_name = "Entrada de Changelog"
        verbose_name_plural = "Entradas de Changelog"
        ordering = ["category", "order", "id_entry"]

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.title}"


class UserVersionRead(models.Model):
    """
    Registro de versiones consultadas y notificaciones leídas por cada usuario.
    Permite asociar la lectura de versiones por usuario sin duplicar registros
    de versión en la arquitectura SaaS compartida de P.M.E.
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="ID Lectura",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="version_reads",
        verbose_name="Usuario",
        db_index=True,
    )
    version = models.ForeignKey(
        SoftwareVersion,
        on_delete=models.CASCADE,
        related_name="user_reads",
        verbose_name="Versión",
        db_index=True,
    )
    read_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de lectura",
    )

    class Meta:
        db_table = "user_version_reads"
        verbose_name = "Lectura de Versión"
        verbose_name_plural = "Lecturas de Versiones"
        unique_together = ("user", "version")
        indexes = [
            models.Index(fields=["user", "version"], name="idx_usr_ver_read"),
            models.Index(fields=["user", "-read_at"], name="idx_usr_read_at"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - v{self.version.version} (read at {self.read_at})"

