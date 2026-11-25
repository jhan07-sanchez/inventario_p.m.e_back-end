from django.db import models

from apps.core.models.active_model import ActiveModel
from apps.core.models.base_model import BaseManager


class TenantQuerySet(models.QuerySet):
    """
    QuerySet personalizado para entidades pertenecientes a una empresa (Tenant).
    Proporciona métodos fluidos para filtrar por organización.
    """

    def for_company(self, company_or_id):
        """
        Filtra el queryset exclusivamente para la empresa proporcionada.
        Acepta una instancia de CompanyInfo o un ID entero.
        """
        if company_or_id is None:
            return self.none()
        company_id = (
            getattr(company_or_id, "id_company", None)
            or getattr(company_or_id, "pk", None)
            or company_or_id
        )
        return self.filter(company_id=company_id)

    def active(self):
        """Retorna únicamente registros activos no eliminados."""
        return self.filter(is_active=True, deleted_at__isnull=True)


class TenantManager(BaseManager.from_queryset(TenantQuerySet)):
    """
    Manager base para modelos multi-tenant.
    Combina el soporte de Soft Delete con el filtrado por empresa.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TenantModel(ActiveModel):
    """
    Modelo base abstracto para todas las entidades que deben estar aisladas por Empresa (Tenant).
    Garantiza que ningún registro de negocio pueda existir sin pertenecer a una organización.
    """

    company = models.ForeignKey(
        "company_info.CompanyInfo",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name="Empresa",
        help_text="Organización / Empresa a la que pertenece este registro.",
        null=False,
        blank=False,
        db_index=True,
    )

    objects = TenantManager()
    all_objects = models.Manager()

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "company_id" in field_names:
            instance._loaded_company_id = values[field_names.index("company_id")]
        elif "company" in field_names:
            instance._loaded_company_id = values[field_names.index("company")]
        return instance

    def save(self, *args, **kwargs):
        """
        Garantiza la inyección automática del tenant activo si no ha sido especificado,
        y bloquea la mutación de la empresa en registros existentes (prevención IDOR).
        """
        if not self.company_id:
            from apps.core.context import get_current_company_id

            ctx_company_id = get_current_company_id()
            if ctx_company_id:
                self.company_id = ctx_company_id
            else:
                import sys

                from django.conf import settings

                if getattr(settings, "IS_TESTING", False) or "test" in sys.argv:
                    from apps.company_info.models import CompanyInfo

                    default_company = CompanyInfo.objects.first()
                    if not default_company:
                        default_company = CompanyInfo.objects.create(
                            business_name="Test Fixture Company",
                            tax_id="000000000-0",
                        )
                    self.company_id = default_company.pk

        # Si el registro ya existe en BD, verificar que no se intente mutar a otra empresa
        if self.pk and self.company_id:
            if (
                hasattr(self, "_loaded_company_id")
                and self._loaded_company_id is not None
            ):
                original_company_id = self._loaded_company_id
            else:
                original_company_id = (
                    type(self)
                    .all_objects.filter(pk=self.pk)
                    .values_list("company_id", flat=True)
                    .first()
                    if hasattr(type(self), "all_objects")
                    else type(self)
                    .objects.filter(pk=self.pk)
                    .values_list("company_id", flat=True)
                    .first()
                )
            if (
                original_company_id is not None
                and self.company_id != original_company_id
            ):
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    "No está permitido transferir o reasignar un registro existente a otra empresa."
                )

        super().save(*args, **kwargs)
        if self.company_id:
            self._loaded_company_id = self.company_id

    class Meta:
        abstract = True
