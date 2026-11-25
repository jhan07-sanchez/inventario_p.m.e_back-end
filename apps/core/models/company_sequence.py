from django.db import models

from apps.core.models.base_model import BaseModel


class CompanySequence(BaseModel):
    """
    Modelo para el control transaccional de secuencias y numeraciones consecutivas
    por empresa y tipo de documento (ej. Ventas, Facturas, Compras).

    Garantiza numeraciones independientes entre organizaciones, unicidad y
    seguridad frente a accesos concurrentes mediante bloqueos a nivel de fila
    (SELECT FOR UPDATE) dentro de transacciones atómicas.
    """

    class DocumentType(models.TextChoices):
        SALE = "SALE", "Venta"
        PURCHASE = "PURCHASE", "Compra"
        INVOICE = "INVOICE", "Factura"
        POS_TICKET = "POS_TICKET", "Ticket POS"

    id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.CASCADE,
        related_name="sequences",
        verbose_name="Empresa",
        help_text="Organización a la que pertenece esta secuencia.",
    )

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        verbose_name="Tipo de documento",
        help_text="Tipo de documento comercial que utiliza este consecutivo.",
    )

    prefix = models.CharField(
        max_length=10,
        default="VTA",
        verbose_name="Prefijo",
        help_text="Prefijo alfanumérico para el documento (ej. VTA, FAC, CMP).",
    )

    current_number = models.PositiveBigIntegerField(
        default=0,
        verbose_name="Número actual",
        help_text="Último número entero emitido para este tipo de documento.",
    )

    padding = models.PositiveSmallIntegerField(
        default=6,
        verbose_name="Relleno de ceros",
        help_text="Cantidad mínima de dígitos con ceros a la izquierda (ej. 6 produce 000001).",
    )

    class Meta:
        db_table = "company_sequences"
        verbose_name = "Secuencia Empresarial"
        verbose_name_plural = "Secuencias Empresariales"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "document_type"],
                name="unique_company_sequence_type",
            )
        ]
        indexes = [
            models.Index(
                fields=["company", "document_type"],
                name="idx_company_seq_type",
            )
        ]

    def __str__(self) -> str:
        return f"Secuencia {self.get_document_type_display()} - Empresa #{self.company_id} ({self.prefix}-{self.current_number:0{self.padding}d})"
