from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel


class Plan(ActiveModel):
    """
    Representa un plan comercial de suscripción para empresas SaaS en P.M.E.
    Define las tarifas, límites de consumo de recursos y módulos habilitados.
    """

    class BillingCycle(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensual"
        ANNUAL = "ANNUAL", "Anual"

    id_plan = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Código del Plan",
        help_text="Identificador único del plan (ej. FREE, BASIC, PRO, ENTERPRISE).",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="Nombre Comercial",
        help_text="Nombre visible para los clientes.",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Precio",
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        verbose_name="Ciclo de Facturación",
    )

    max_users = models.PositiveIntegerField(
        default=1,
        verbose_name="Máximo de Usuarios",
        help_text="Cantidad máxima de usuarios/miembros activos permitidos.",
    )

    max_products = models.PositiveIntegerField(
        default=100,
        verbose_name="Máximo de Productos",
        help_text="Cantidad máxima de productos en el catálogo.",
    )

    max_invoices_per_month = models.PositiveIntegerField(
        default=100,
        verbose_name="Máximo de Facturas/Mes",
        help_text="Límite mensual de comprobantes emitidos.",
    )

    enabled_modules = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Módulos Habilitados",
        help_text="Lista de códigos de módulos con acceso autorizado (ej: ['inventory', 'sales', 'finance', 'cash', 'invoices']).",
    )

    class Meta:
        db_table = "plans"
        verbose_name = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"
        ordering = ["price", "name"]
        indexes = [
            models.Index(fields=["code"], name="plan_code_idx"),
            models.Index(fields=["is_active"], name="plan_is_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code}) - ${self.price}/{self.get_billing_cycle_display()}"

