from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models.base_model import BaseModel


class CompanyMembership(BaseModel):
    """
    Modelo representativo de la vinculación (Membresía) entre un Usuario y una Empresa.
    Permite que un usuario pertenezca a múltiples organizaciones con diferentes roles y permisos.
    """

    class MembershipStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        INVITED = "INVITED", "Invitado"
        SUSPENDED = "SUSPENDED", "Suspendida"

    id_membership = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Usuario",
        help_text="Usuario perteneciente a la empresa.",
    )

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Empresa",
        help_text="Organización a la que se vincula el usuario.",
    )

    role = models.ForeignKey(
        "users.Role",
        on_delete=models.PROTECT,
        related_name="memberships",
        verbose_name="Rol en la Empresa",
        help_text="Rol que determina los permisos del usuario dentro de esta empresa.",
    )

    is_owner = models.BooleanField(
        default=False,
        verbose_name="¿Es Propietario?",
        help_text="Indica si el usuario es el dueño / creador principal de la organización.",
    )

    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
        verbose_name="Estado de Membresía",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Estado",
        help_text="Indica si la membresía se encuentra activa.",
    )

    history = HistoricalRecords()

    class Meta:
        db_table = "company_memberships"
        verbose_name = "Membresía Empresarial"
        verbose_name_plural = "Membresías Empresariales"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"],
                name="unique_user_company_membership",
            )
        ]

        indexes = [
            models.Index(fields=["user", "is_active"], name="membership_user_active_idx"),
            models.Index(fields=["company", "is_active"], name="membership_comp_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.company.trade_name or self.company.business_name} ({self.role.role_name})"


    def save(self, *args, **kwargs):
        """
        Sincronizacion automaticamente de estados (Defense in Depth).
        evita que una membresia suspendida siga teniendo is_active = True, o que una membresia activa tenga status = SUSPENDED.
        """
        if self.status == self.MembershipStatus.SUSPENDED:
            self.is_active = False
        elif self.status == self.MembershipStatus.ACTIVE:
            self.is_active = True

        super().save(*args, **kwargs)
