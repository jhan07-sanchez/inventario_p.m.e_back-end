from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models.active_model import ActiveModel
from apps.subscriptions.models.plan import Plan


class Subscription(ActiveModel):
    """
    Representa la suscripción activa o histórica de una empresa a un plan comercial.
    Controla el ciclo de vida del acceso SaaS y los períodos de gracia ante mora.
    """

    class Status(models.TextChoices):
        TRIAL = "TRIAL", "Prueba Gratuita"
        ACTIVE = "ACTIVE", "Activa"
        PAST_DUE = "PAST_DUE", "Pago Pendiente (En Gracia)"
        CANCELLED = "CANCELLED", "Cancelada"
        EXPIRED = "EXPIRED", "Expirada"

    id_subscription = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Empresa",
        db_index=True,
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name="Plan Contratado",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
        db_index=True,
        verbose_name="Estado de Suscripción",
    )

    start_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Inicio",
    )

    end_date = models.DateTimeField(
        verbose_name="Fecha de Vencimiento",
    )

    grace_period_days = models.PositiveIntegerField(
        default=5,
        verbose_name="Días de Gracia",
        help_text="Días adicionales permitidos para regularizar pago tras la fecha de vencimiento.",
    )

    auto_renew = models.BooleanField(
        default=True,
        verbose_name="Renovación Automática",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas de Suscripción",
    )

    class Meta:
        db_table = "subscriptions"
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["company", "status"], name="sub_comp_status_idx"),
            models.Index(fields=["status", "end_date"], name="sub_status_end_idx"),
        ]

    def __str__(self) -> str:
        return f"Suscripción #{self.id_subscription} - {self.company} ({self.plan.name}) [{self.get_status_display()}]"

    @property
    def is_in_grace_period(self) -> bool:
        """Determina si la suscripción vencida se encuentra aún dentro del período de gracia."""
        now = timezone.now()
        if now <= self.end_date:
            return False
        grace_deadline = self.end_date + timedelta(days=self.grace_period_days)
        return now <= grace_deadline

    @property
    def is_valid(self) -> bool:
        """
        Determina si el inquilino tiene derecho operativo sobre el software.
        Válido si está en TRIAL/ACTIVE vigente o si está en período de gracia.
        """
        if not self.is_active or self.status == self.Status.CANCELLED:
            return False

        now = timezone.now()
        if self.status in [self.Status.TRIAL, self.Status.ACTIVE]:
            return now <= self.end_date or self.is_in_grace_period

        if self.status == self.Status.PAST_DUE:
            return self.is_in_grace_period

        return False

    @property
    def days_remaining(self) -> int:
        """Retorna los días restantes de servicio o 0 si ya venció."""
        now = timezone.now()
        if self.end_date > now:
            return (self.end_date - now).days
        return 0
