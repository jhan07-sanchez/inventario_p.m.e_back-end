from django.db import models

from apps.core.models.base_model import BaseModel


class Supplier(BaseModel):
    """
    Modelo que representa un proveedor en el sistema inventario-pme.
    """

    class DocumentType(models.TextChoices):
        """
        Tipos de documento que un proveedor puede tener.
        """

        CC = "CC", "Cédula de Ciudadanía"
        NIT = "NIT", "Número de Identificación Tributaria"
        CE = "CE", "Cédula de Extranjería"
        PAS = "PAS", "Pasaporte"
        TI = "TI", "Tarjeta de Identidad"

    id_supplier = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    document_type = models.CharField(
        max_length=10,
        choices=DocumentType.choices,
        verbose_name="Tipo de Documento",
        help_text=("Tipo de documento del proveedor (CC, NIT, CE, PAS, TI)."),
    )

    document_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Número de Documento",
        help_text="Número único de identificación del proveedor.",
    )

    first_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nombres",
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Apellidos",
    )

    business_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Razón Social",
        help_text=("Nombre de la empresa o razón social del proveedor."),
    )

    email = models.EmailField(
        max_length=254,
        blank=True,
        verbose_name="Correo Electrónico",
        help_text="Correo electrónico del proveedor.",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono",
        help_text="Número de teléfono del proveedor.",
    )

    mobile = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Celular",
        help_text="Número de celular del proveedor.",
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Dirección",
        help_text="Dirección física del proveedor.",
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ciudad",
        help_text="Ciudad de ubicación del proveedor.",
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="País",
        help_text="País de ubicación del proveedor.",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
        help_text="Notas adicionales sobre el proveedor.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Estado",
        help_text=("Indica si el proveedor está activo en el sistema."),
    )

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "Proveedores"
        db_table = "suppliers"
        ordering = ["id_supplier"]

        indexes = [
            models.Index(
                fields=["document_number"],
                name="supplier_document_idx",
            ),
            models.Index(
                fields=["is_active"],
                name="supplier_active_idx",
            ),
            models.Index(
                fields=["last_name"],
                name="supplier_last_name_idx",
            ),
            models.Index(
                fields=["business_name"],
                name="supplier_business_name_idx",
            ),
        ]

    def __str__(self) -> str:
        """
        Devuelve una representación legible del proveedor.
        """

        if self.business_name:
            return self.business_name

        full_name = f"{self.first_name} {self.last_name}".strip()

        return full_name or self.document_number
