from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.invoices.models.invoice_template import InvoiceTemplate


class Invoice(ActiveModel):
    """
    Modelo que representa una factura o documento empresarial (compra/venta).
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        ISSUED = "ISSUED", "Emitida"
        CANCELLED = "CANCELLED", "Anulada"
        
    class DocumentType(models.TextChoices):
        PURCHASE_INVOICE = "PURCHASE_INVOICE", "Factura de Compra"
        SALE_INVOICE = "SALE_INVOICE", "Factura de Venta"

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número de Factura",
    )
    
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        verbose_name="Tipo de documento",
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Estado de la factura",
    )
    
    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de emisión",
    )
    
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento",
    )
    
    template = models.ForeignKey(
        InvoiceTemplate,
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name="Plantilla documental",
    )
    
    purchase = models.ForeignKey(
        "purchases.Purchase",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        verbose_name="Compra relacionada",
    )

    sale = models.ForeignKey(
        "sales.Sale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        verbose_name="Venta relacionada",
    )
    
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Subtotal",
    )
    
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Descuento",
    )
    
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Impuestos",
    )
    
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Total",
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
    )

    # --- Snapshots Históricos de Empresa ---
    # Para cumplir requerimientos legales, la factura congela los datos 
    # de la empresa al momento de su emisión.
    company_name_snapshot = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Nombre Empresa (Snapshot)",
    )
    
    company_tax_id_snapshot = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="NIT Empresa (Snapshot)",
    )
    
    company_address_snapshot = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Dirección Empresa (Snapshot)",
    )
    
    company_phone_snapshot = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Teléfono Empresa (Snapshot)",
    )
    
    company_email_snapshot = models.EmailField(
        max_length=254,
        blank=True,
        default="",
        verbose_name="Correo Empresa (Snapshot)",
    )

    class Meta:
        db_table = "invoices"
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["invoice_number"], name="invoice_number_idx"),
            models.Index(fields=["status"], name="invoice_status_idx"),
            models.Index(fields=["document_type", "status"], name="invoice_type_status_idx"),
            models.Index(fields=["purchase"], name="invoice_purchase_idx"),
            models.Index(fields=["sale"], name="invoice_sale_idx"),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(purchase__isnull=False, sale__isnull=True)
                    | models.Q(purchase__isnull=True, sale__isnull=False)
                ),
                name="invoice_exactly_one_origin",
            ),
        ]

    def __str__(self) -> str:
        return f"Factura {self.invoice_number} ({self.get_status_display()})"
