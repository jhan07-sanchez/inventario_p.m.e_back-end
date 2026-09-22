from django.db import transaction
from django.core.exceptions import ValidationError

from apps.core.services.base_service import BaseService
from apps.invoices.dto.invoice_template_dto import InvoiceTemplateCreateDTO, InvoiceTemplateUpdateDTO
from apps.invoices.models import InvoiceTemplate


class InvoiceTemplateService(BaseService[InvoiceTemplate]):
    """
    Servicio encargado de la lógica de plantillas de facturas.
    """

    def __init__(self):
        super().__init__(InvoiceTemplate)

    @staticmethod
    @transaction.atomic
    def create_template(dto: InvoiceTemplateCreateDTO) -> InvoiceTemplate:
        # Si se marca como default, desactivar otros default para ese tipo
        if dto.is_default:
            InvoiceTemplate.objects.filter(
                document_type=dto.document_type, is_default=True
            ).update(is_default=False)

        return InvoiceTemplate.objects.create(
            name=dto.name,
            document_type=dto.document_type,
            header_content=dto.header_content,
            footer_content=dto.footer_content,
            is_default=dto.is_default,
        )

    @staticmethod
    @transaction.atomic
    def update_template(template: InvoiceTemplate, dto: InvoiceTemplateUpdateDTO) -> InvoiceTemplate:
        if dto.name is not None:
            template.name = dto.name
        if dto.header_content is not None:
            template.header_content = dto.header_content
        if dto.footer_content is not None:
            template.footer_content = dto.footer_content

        if dto.is_default is not None:
            if dto.is_default and not template.is_default:
                InvoiceTemplate.objects.filter(
                    document_type=template.document_type, is_default=True
                ).exclude(pk=template.pk).update(is_default=False)
            template.is_default = dto.is_default

        template.save(update_fields=["name", "header_content", "footer_content", "is_default", "updated_at"])
        return template

    @staticmethod
    @transaction.atomic
    def deactivate_template(template: InvoiceTemplate) -> None:
        if not template.is_active:
            raise ValidationError("La plantilla ya se encuentra inactiva.")
        
        InvoiceTemplateService().delete(template)

    @staticmethod
    @transaction.atomic
    def restore_template(template: InvoiceTemplate) -> InvoiceTemplate:
        """
        Restaura una plantilla de factura previamente desactivada.
        """

        if template.is_active:
            return template

        return InvoiceTemplateService().restore(template)
