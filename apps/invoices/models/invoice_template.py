from django.db import models

from apps.core.models.active_model import ActiveModel


class InvoiceTemplate(ActiveModel):
    """
    Modelo que representa una plantilla documental para
    la generación de facturas u otros documentos empresariales.
    """

    class DocumentType(models.TextChoices):
        PURCHASE_INVOICE = "PURCHASE_INVOICE", "Factura de Compra"
        SALE_INVOICE = "SALE_INVOICE", "Factura de Venta"
        POS_TICKET = "POS_TICKET", "Ticket POS"

    name = models.CharField(
        max_length=150,
        verbose_name="Nombre de la plantilla",
        help_text="Ej: Plantilla estándar de Factura de Venta",
    )

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        verbose_name="Tipo de documento",
    )

    header_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="Contenido del encabezado",
        help_text="Contenido en formato texto o HTML para el encabezado.",
    )

    body_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="Contenido del cuerpo",
        help_text="Contenido HTML para el cuerpo (ej. tabla de productos con variables dinámicas).",
    )

    footer_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="Contenido del pie de página",
        help_text="Contenido en formato texto o HTML para el pie de página.",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="Plantilla por defecto",
        help_text="Indica si es la plantilla principal para el tipo de documento especificado.",
    )

    class Meta:
        db_table = "invoice_templates"
        verbose_name = "Plantilla de Factura"
        verbose_name_plural = "Plantillas de Factura"
        ordering = ["-is_default", "name"]

        indexes = [
            models.Index(fields=["document_type", "is_active"], name="inv_tmpl_type_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_document_type_display()})"
