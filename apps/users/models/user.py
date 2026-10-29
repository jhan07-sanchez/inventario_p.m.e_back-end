from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.core.models.base_model import BaseModel

from ..managers import UserManager
from ..validators import document_number_validator


class User(AbstractUser, BaseModel):
    """
    Modelo de usuario personalizado para inventario-pme.
    """

    id_user = models.BigAutoField(primary_key=True, verbose_name="ID")
    document_number = models.CharField(
        unique=True,
        validators=[document_number_validator],
        max_length=50,
        verbose_name="Número de documento",
        help_text="Número de documento de identidad del usuario.",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Correo electrónico",
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Teléfono",
        help_text="Número telefónico del usuario.",
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Intentos fallidos",
        help_text="Numero de intentos de inicio de sesion fallidos consecutivos."
    )
    lockout_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bloqueado hasta",
        help_text="Fecha y hora la cual la cuenta esta bloqueada."
    )
    history = HistoricalRecords(excluded_fields=["password", "last_login", "date_joined"])

    @property
    def is_locked_out(self) -> bool:
        """Verifica si el usuario esta actualmente bloqueado."""
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        return False

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["id_user"]

        indexes = [
            models.Index(
                fields=["is_active"],
                name="user_is_active_idx",
            ),
            models.Index(
                fields=["deleted_at"],
                name="user_deleted_at_idx",
            ),
        ]

    def __str__(self):
        return self.username
