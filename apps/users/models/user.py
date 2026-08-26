from django.contrib.auth.models import AbstractUser
from django.db import models

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

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["id_user"]

    def __str__(self):
        return self.username
