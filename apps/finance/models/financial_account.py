from decimal import Decimal


from django.db import models

from apps.core.models.active_model import ActiveModel


class FinancialAccount(ActiveModel):
    """
    Modelo que representa una cuenta en la que la empresa administra dinero:
    caja de tesorería, cuenta corriente bancaria, cuenta de ahorros, billetera digital, etc.
    """

    class AccountType(models.TextChoices):
        CASH = "CASH", "Caja de Efectivo"
        BANK = "BANK", "Cuenta Bancaria"
        DIGITAL_WALLET = "DIGITAL_WALLET", "Billetera Digital"
        CREDIT = "CREDIT", "Línea de Crédito"
        OTHER = "OTHER", "Otra"

    id_financial_account = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    name = models.CharField(
        max_length=120,
        verbose_name="Nombre de la Cuenta",
        help_text="Ej: Caja Principal Tesorería, Bancolombia Ahorros 1234, Davivienda Corriente",
    )

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.BANK,
        db_index=True,
        verbose_name="Tipo de Cuenta",
    )

    account_number = models.CharField(
        max_length=60,
        blank=True,
        default="",
        verbose_name="Número de Cuenta / Identificador",
        help_text="Número de cuenta bancaria o ID de la billetera.",
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Entidad Financiera",
        help_text="Nombre de la entidad (ej: Bancolombia, Davivienda, Nequi, Daviplata).",
    )

    currency = models.CharField(
        max_length=10,
        default="COP",
        verbose_name="Moneda",
    )

    initial_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Saldo Inicial",
        help_text="Saldo con el que se abrió o registró la cuenta en el sistema.",
    )

    current_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Saldo Actual",
        help_text="Saldo actualizado en tiempo real a partir de transacciones y movimientos.",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción / Observaciones",
    )

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="financial_accounts",
        verbose_name="Empresa",
    )

    class Meta:
        db_table = "financial_accounts"
        verbose_name = "Cuenta Financiera"
        verbose_name_plural = "Cuentas Financieras"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["account_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["company"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "company"],
                condition=models.Q(is_active=True),
                name="unique_account_name_per_company_active",
            ),
        ]

    def __str__(self) -> str:
        suffix = f" ({self.bank_name})" if self.bank_name else ""
        return f"{self.name}{suffix} - ${self.current_balance:,.2f}"

