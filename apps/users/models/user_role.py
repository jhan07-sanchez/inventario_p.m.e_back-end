from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models.base_model import BaseModel
from apps.users.models.role import Role
from apps.users.models.user import User


class UserRole(BaseModel):
    """
    Modelo encargado de almacenar la asignación
    de roles a los usuarios.
    """

    id_user_role = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name="Usuario",
        help_text="Usuario al que pertenece el rol.",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name="Rol",
        help_text="Rol asignado al usuario.",
    )
    history = HistoricalRecords()

    class Meta:
        db_table = "user_roles"

        verbose_name = "Asignación de Rol"

        verbose_name_plural = "Asignaciones de Roles"

        ordering = [
            "id_user_role",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "role",
                ],
                name="unique_user_role",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role.role_name}"
