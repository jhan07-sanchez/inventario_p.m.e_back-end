import uuid

from django.conf import settings
from django.db import models

from apps.core.models.active_model import ActiveModel


class CompanyInfo(ActiveModel):
    """
    Modelo representativo de una Empresa / Organización en la plataforma SaaS.
    Almacena los datos fiscales, comerciales y operativos de cada tenant.
    """

    class CompanyStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        SUSPENDED = "SUSPENDED", "Suspendida"
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pendiente de Verificación"
        CANCELLED = "CANCELLED", "Cancelada"

    id_company = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        null=True,
        db_index=True,
        verbose_name="UUID Público",
        help_text="Identificador único universal para integraciones y API pública.",
    )

    status = models.CharField(
        max_length=25,
        choices=CompanyStatus.choices,
        default=CompanyStatus.ACTIVE,
        db_index=True,
        verbose_name="Estado de la Empresa",
        help_text="Estado operativo de la organización en la plataforma SaaS.",
    )

    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_companies",
        verbose_name="Propietario Principal",
        help_text="Usuario propietario/creador de la organización.",
    )

    business_name = models.CharField(
        max_length=200,
        verbose_name="Razón Social",
        help_text="Razón social o nombre legal de la empresa.",
    )

    trade_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Nombre Comercial",
        help_text="Nombre comercial o marca de la empresa.",
    )

    tax_id = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="NIT / Identificación Fiscal",
        help_text="Número de Identificación Tributaria de la empresa.",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Teléfono",
        help_text="Teléfono principal de la empresa.",
    )

    mobile = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Celular",
        help_text="Número de celular de la empresa.",
    )

    email = models.EmailField(
        max_length=254,
        blank=True,
        default="",
        verbose_name="Correo Electrónico",
        help_text="Correo electrónico principal de la empresa.",
    )

    website = models.URLField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Sitio Web",
        help_text="URL del sitio web de la empresa.",
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Dirección",
        help_text="Dirección física de la empresa.",
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Ciudad",
        help_text="Ciudad donde se ubica la empresa.",
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Departamento",
        help_text="Departamento o estado de la empresa.",
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        default="Colombia",
        verbose_name="País",
        help_text="País donde se ubica la empresa.",
    )

    logo = models.ImageField(
        upload_to="company/logo/",
        blank=True,
        null=True,
        verbose_name="Logo",
        help_text="Logo de la empresa.",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
        help_text="Descripción breve de la empresa.",
    )

    receipt_footer = models.TextField(
        blank=True,
        default="Gracias por su compra",
        verbose_name="Pie de Ticket",
        help_text="Texto que aparece al final del ticket POS.",
    )

    class Meta:
        db_table = "company_info"
        verbose_name = "Información de Empresa"
        verbose_name_plural = "Información de Empresa"
        ordering = ["id_company"]

        indexes = [
            models.Index(
                fields=["tax_id"],
                name="company_tax_id_idx",
            ),
            models.Index(
                fields=["is_active"],
                name="company_active_idx",
            ),
        ]

    def __str__(self) -> str:
        """Retorna una representación legible de la empresa."""
        return self.trade_name or self.business_name
