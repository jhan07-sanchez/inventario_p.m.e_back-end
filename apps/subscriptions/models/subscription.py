import math
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
        """
        Determina si la suscripción vencida se encuentra aún dentro del período de gracia.
        REGLA DE NEGOCIO:
        - TRIAL: NUNCA tiene período de gracia. Retorna False siempre.
        - CANCELLED o EXPIRED: NUNCA están en período de gracia.
        - ACTIVE o PAST_DUE: True si now > end_date y now <= end_date + grace_period_days, con grace_period_days > 0.
        """
        if self.status in [self.Status.TRIAL, self.Status.CANCELLED, self.Status.EXPIRED]:
            return False

        if not self.grace_period_days or self.grace_period_days <= 0:
            return False

        now = timezone.now()
        if now <= self.end_date:
            return False

        grace_deadline = self.end_date + timedelta(days=self.grace_period_days)
        return now <= grace_deadline

    @property
    def is_expired(self) -> bool:
        """
        Determina si la suscripción está vencida definitivamente.
        - EXPIRED o CANCELLED explícito -> True.
        - Inactiva (is_active=False) -> True.
        - TRIAL: Vencida si now > end_date (sin período de gracia).
        - ACTIVE / PAST_DUE: Vencida si now > end_date + grace_period_days (o now > end_date si grace_period_days <= 0).
        """
        if not self.is_active or self.status in [self.Status.EXPIRED, self.Status.CANCELLED]:
            return True

        now = timezone.now()
        if self.status == self.Status.TRIAL:
            return now > self.end_date

        if self.status in [self.Status.ACTIVE, self.Status.PAST_DUE]:
            grace_days = self.grace_period_days if self.grace_period_days else 0
            deadline = self.end_date + timedelta(days=grace_days)
            return now > deadline

        return True

    @property
    def is_valid(self) -> bool:
        """
        Determina si el inquilino tiene derecho operativo sobre el software.
        Es válida si no ha expirado según sus reglas específicas.
        """
        return not self.is_expired

    @property
    def is_read_only(self) -> bool:
        """
        Determina si la cuenta de la empresa está en modo de SOLO LECTURA.
        Aplica cuando la suscripción ha expirado, está cancelada o inactiva.
        """
        return self.is_expired

    @property
    def can_write(self) -> bool:
        """
        Determina si la suscripción autoriza operaciones de escritura (mutación de datos).
        Inverso estricto de is_read_only.
        """
        return not self.is_read_only

    @property
    def days_remaining(self) -> int:
        """Retorna los días restantes de servicio redondeando hacia arriba. 0 si ya venció."""
        now = timezone.now()
        if self.end_date > now:
            diff = self.end_date - now
            return math.ceil(diff.total_seconds() / (24 * 3600))
        return 0

    @property
    def days_overdue(self) -> int:
        """Retorna la cantidad de días transcurridos desde end_date si ya venció. 0 si aún está vigente."""
        now = timezone.now()
        if now > self.end_date:
            diff = now - self.end_date
            return math.ceil(diff.total_seconds() / (24 * 3600))
        return 0
