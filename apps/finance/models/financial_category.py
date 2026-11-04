from django.db import models

from apps.core.models.active_model import ActiveModel


class FinancialCategory(ActiveModel):
    """
    Categorías para clasificar los movimientos de entrada y salida de tesorería:
    (ej: Ingreso por Ventas, Pago a Proveedores, Servicios Públicos, Nómina, Impuestos, Mantenimiento).
    """

    class CategoryType(models.TextChoices):
        INFLOW = "INFLOW", "Ingreso"
        OUTFLOW = "OUTFLOW", "Egreso"
        BOTH = "BOTH", "Ambos / Mixto"

    id_financial_category = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    name = models.CharField(
        max_length=120,
        verbose_name="Nombre de la Categoría",
    )

    category_type = models.CharField(
        max_length=10,
        choices=CategoryType.choices,
        default=CategoryType.OUTFLOW,
        db_index=True,
        verbose_name="Tipo de Categoría",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="financial_categories",
        verbose_name="Empresa",
    )

    class Meta:
        db_table = "financial_categories"
        verbose_name = "Categoría Financiera"
        verbose_name_plural = "Categorías Financieras"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category_type"]),
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "company"],
                condition=models.Q(is_active=True),
                name="unique_financial_category_per_company_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_type_display()})"

