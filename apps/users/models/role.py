from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models.base_model import BaseModel


class Role(BaseModel):
    """
    Modelo de roles y permisos del sistema.
    """

    id_role = models.BigAutoField(primary_key=True, verbose_name="ID")
    role_name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre del rol",
        help_text="Nombre único del rol.",
    )
    role_description = models.TextField(
        blank=True, null=True, verbose_name="Descripción"
    )

    permissions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Permisos dinámicos",
        help_text=(
            "Diccionario JSON con los permisos del rol. "
            'Ejemplo: {"users.view": true, "sales.create": false}'
        ),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Estado",
        help_text="Indica si el registro está activo.",
    )
    history = HistoricalRecords()

    class Meta:
        db_table = "roles"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["id_role"]

        indexes = [
            models.Index(fields=["role_name"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.role_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.core.cache import cache

        cache.clear()
