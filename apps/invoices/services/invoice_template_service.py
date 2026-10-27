import re
from typing import Optional

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.services.base_service import BaseService
from apps.invoices.dto.invoice_template_dto import (
    InvoiceTemplateCreateDTO,
    InvoiceTemplateUpdateDTO,
)
from apps.invoices.models import InvoiceTemplate


class InvoiceTemplateService(BaseService[InvoiceTemplate]):
    """
    Servicio encargado de la lógica de plantillas de facturas.
    """

    ALLOWED_TEMPLATE_VARIABLES = {
        # Company variables
        "company_name",
        "company_tax_id",
        "company_phone",
        "company_address",
        "company_email",
        "company_city",
        "company_receipt_footer",
        # Document variables
        "document_number",
        "document_date",
        "customer_name",
        "subtotal",
        "discount",
        "tax",
        "total",
        "amount_received",
        "change_amount",
        # Loop tags
        "#items",
        "/items",
        # Item variables
        "item_name",
        "product_name",
        "item_quantity",
        "quantity",
        "item_price",
        "unit_price",
        "price",
        "item_subtotal",
    }

    DANGEROUS_PATTERNS = [
        re.compile(r"<\s*script\b", re.IGNORECASE),
        re.compile(r"<\s*/\s*script\b", re.IGNORECASE),
        re.compile(r"<\s*iframe\b", re.IGNORECASE),
        re.compile(r"<\s*object\b", re.IGNORECASE),
        re.compile(r"<\s*embed\b", re.IGNORECASE),
        re.compile(r"<\s*applet\b", re.IGNORECASE),
        re.compile(r"\bon[a-zA-Z]+\s*=", re.IGNORECASE),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"vbscript\s*:", re.IGNORECASE),
    ]

    def __init__(self):
        super().__init__(InvoiceTemplate)

    @classmethod
    def validate_content_security(cls, content: Optional[str]) -> None:
        """
        Valida que el contenido HTML de la plantilla no incluya scripts ejecutables
        ni elementos maliciosos.
        """
        if not content:
            return

        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(content):
                raise ValidationError(
                    "El contenido de la plantilla contiene código ejecutable o etiquetas no permitidas "
                    "(scripts, iframes, manejadores de eventos o javascript:)."
                )

    @classmethod
    def validate_placeholders(cls, *contents: Optional[str]) -> None:
        """
        Valida que los marcadores de posición {{ variable }} y bucles {{#items}}
        sean válidos y estén balanceados.
        """
        for content in contents:
            if not content:
                continue

            open_loops = len(re.findall(r"\{\{#items\}\}", content))
            close_loops = len(re.findall(r"\{\{/items\}\}", content))
            if open_loops != close_loops:
                raise ValidationError(
                    f"Las etiquetas de bucle de ítems ({{{{#items}}}} y {{{{/items}}}}) no están balanceadas "
                    f"({open_loops} abiertas vs {close_loops} cerradas)."
                )

            matches = re.findall(r"\{\{\s*([#\/]?[a-zA-Z0-9_]+)\s*\}\}", content)
            for var in matches:
                clean_var = var.strip()
                if clean_var not in cls.ALLOWED_TEMPLATE_VARIABLES:
                    raise ValidationError(
                        f"Variable no permitida o desconocida en la plantilla: '{{{{ {clean_var} }}}}'. "
                        f"Consulte el catálogo de variables permitidas para plantillas."
                    )

    @classmethod
    def preview_template(
        cls,
        template: InvoiceTemplate,
        sample_data: Optional[dict] = None,
    ) -> dict:
        """
        Genera una vista previa renderizada de la plantilla con datos de ejemplo y
        la información corporativa activa actual, sin persistir ninguna factura.
        """
        from apps.company_info.selectors.company_info_selector import (
            CompanyInfoSelector,
        )

        company = CompanyInfoSelector.get_current()
        comp_name = company.business_name if company else "Inventario P.M.E"
        comp_tax_id = f"NIT: {company.tax_id}" if company and company.tax_id else ""
        comp_phone = (company.phone or company.mobile) if company else ""
        comp_address = company.address if company else ""
        comp_email = company.email if company else ""
        comp_city = company.city if company else ""
        comp_footer = company.receipt_footer if company else ""

        doc_data = sample_data or {}
        doc_number = doc_data.get("document_number", "FAC-000001")
        doc_date = doc_data.get("document_date", "2026-10-26")
        customer_name = doc_data.get("customer_name", "Cliente de Prueba S.A.S.")
        subtotal = doc_data.get("subtotal", "$47,000.00")
        discount = doc_data.get("discount", "$0.00")
        tax = doc_data.get("tax", "$8,930.00")
        total = doc_data.get("total", "$55,930.00")
        amount_received = doc_data.get("amount_received", "$60,000.00")
        change_amount = doc_data.get("change_amount", "$4,070.00")

        replacements = {
            "company_name": comp_name,
            "company_tax_id": comp_tax_id,
            "company_phone": comp_phone,
            "company_address": comp_address,
            "company_email": comp_email,
            "company_city": comp_city,
            "company_receipt_footer": comp_footer,
            "document_number": doc_number,
            "document_date": doc_date,
            "customer_name": customer_name,
            "subtotal": str(subtotal),
            "discount": str(discount),
            "tax": str(tax),
            "total": str(total),
            "amount_received": str(amount_received),
            "change_amount": str(change_amount),
        }

        sample_items = doc_data.get("items") or [
            {
                "product_name": "Tornillo Drywall 1/2 pulg (Caja x 100)",
                "quantity": 2,
                "unit_price": "$15,000.00",
                "subtotal": "$30,000.00",
            },
            {
                "product_name": "Martillo de Uña 16oz Mango Fibra",
                "quantity": 1,
                "unit_price": "$17,000.00",
                "subtotal": "$17,000.00",
            },
        ]

        def _render_section(content: Optional[str]) -> str:
            if not content:
                return ""
            parsed = content
            for key, val in replacements.items():
                pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
                parsed = re.sub(pattern, lambda _m, v=val: v, parsed)

            loop_pattern = re.compile(r"\{\{#items\}\}([\s\S]*?)\{\{/items\}\}")

            def _replace_loop(match):
                item_tmpl = match.group(1)
                rows = []
                for item in sample_items:
                    row = item_tmpl
                    p_name = item.get("product_name") or item.get(
                        "item_name", "Producto"
                    )
                    qty = str(item.get("quantity") or item.get("item_quantity", 1))
                    price = str(
                        item.get("unit_price") or item.get("item_price", "$0.00")
                    )
                    subt = str(
                        item.get("subtotal") or item.get("item_subtotal", "$0.00")
                    )
                    row = re.sub(r"\{\{\s*(item_name|product_name)\s*\}\}", p_name, row)
                    row = re.sub(r"\{\{\s*(item_quantity|quantity)\s*\}\}", qty, row)
                    row = re.sub(
                        r"\{\{\s*(item_price|unit_price|price)\s*\}\}", price, row
                    )
                    row = re.sub(r"\{\{\s*(item_subtotal|subtotal)\s*\}\}", subt, row)
                    rows.append(row)
                return "".join(rows)

            parsed = loop_pattern.sub(_replace_loop, parsed)
            return parsed

        rendered_header = _render_section(template.header_content)
        rendered_body = _render_section(template.body_content)
        rendered_footer = _render_section(template.footer_content)

        full_html = (
            f'<div class="document-render-container" style="font-family: \'Courier New\', Courier, monospace; font-size: 12px; margin: 0 auto; width: 100%;">'
            f'<div class="document-header" style="text-align: center;">{rendered_header}</div>'
            f'<div class="document-body">{rendered_body}</div>'
            f'<div class="document-footer" style="text-align: center;">{rendered_footer}</div>'
            f"</div>"
        )

        return {
            "template_id": template.pk,
            "name": template.name,
            "document_type": template.document_type,
            "rendered_header": rendered_header,
            "rendered_body": rendered_body,
            "rendered_footer": rendered_footer,
            "full_html": full_html,
        }

    @staticmethod
    @transaction.atomic
    def set_default(template: InvoiceTemplate) -> InvoiceTemplate:
        """
        Establece la plantilla indicada como la predeterminada para su tipo de documento,
        desactivando cualquier otra plantilla por defecto existente del mismo tipo.
        """
        InvoiceTemplate.objects.filter(
            document_type=template.document_type,
            is_default=True,
        ).exclude(pk=template.pk).update(is_default=False)

        template.is_default = True
        template.save(update_fields=["is_default", "updated_at"])

        cache.delete(f"invoice_default_template_{template.document_type}")
        return template

    @staticmethod
    @transaction.atomic
    def create_template(dto: InvoiceTemplateCreateDTO) -> InvoiceTemplate:
        # Validar seguridad y variables
        InvoiceTemplateService.validate_content_security(dto.header_content)
        InvoiceTemplateService.validate_content_security(dto.body_content)
        InvoiceTemplateService.validate_content_security(dto.footer_content)
        InvoiceTemplateService.validate_placeholders(
            dto.header_content, dto.body_content, dto.footer_content
        )
        # Si se marca como default, desactivar otros default para ese tipo
        if dto.is_default:
            InvoiceTemplate.objects.filter(
                document_type=dto.document_type, is_default=True
            ).update(is_default=False)

        template = InvoiceTemplate.objects.create(
            name=dto.name,
            document_type=dto.document_type,
            header_content=dto.header_content,
            body_content=dto.body_content,
            footer_content=dto.footer_content,
            is_default=dto.is_default,
        )

        cache.delete(f"invoice_default_template_{dto.document_type}")
        return template

    @staticmethod
    @transaction.atomic
    def update_template(
        template: InvoiceTemplate, dto: InvoiceTemplateUpdateDTO
    ) -> InvoiceTemplate:
        header_to_check = (
            dto.header_content
            if dto.header_content is not None
            else template.header_content
        )
        body_to_check = (
            dto.body_content if dto.body_content is not None else template.body_content
        )
        footer_to_check = (
            dto.footer_content
            if dto.footer_content is not None
            else template.footer_content
        )

        if dto.header_content is not None:
            InvoiceTemplateService.validate_content_security(dto.header_content)
        if dto.body_content is not None:
            InvoiceTemplateService.validate_content_security(dto.body_content)
        if dto.footer_content is not None:
            InvoiceTemplateService.validate_content_security(dto.footer_content)

        InvoiceTemplateService.validate_placeholders(
            header_to_check, body_to_check, footer_to_check
        )

        if dto.name is not None:
            template.name = dto.name
        if dto.header_content is not None:
            template.header_content = dto.header_content
        if dto.body_content is not None:
            template.body_content = dto.body_content
        if dto.footer_content is not None:
            template.footer_content = dto.footer_content

        if dto.is_default is not None:
            if dto.is_default and not template.is_default:
                InvoiceTemplate.objects.filter(
                    document_type=template.document_type, is_default=True
                ).exclude(pk=template.pk).update(is_default=False)
            template.is_default = dto.is_default

        template.save(
            update_fields=[
                "name",
                "header_content",
                "body_content",
                "footer_content",
                "is_default",
                "updated_at",
            ]
        )

        cache.delete(f"invoice_default_template_{template.document_type}")
        return template

    @staticmethod
    @transaction.atomic
    def deactivate_template(template: InvoiceTemplate) -> None:
        if not template.is_active:
            raise ValidationError("La plantilla ya se encuentra inactiva.")

        InvoiceTemplateService().delete(template)
        cache.delete(f"invoice_default_template_{template.document_type}")

    @staticmethod
    @transaction.atomic
    def restore_template(template: InvoiceTemplate) -> InvoiceTemplate:
        """
        Restaura una plantilla de factura previamente desactivada.
        """

        if template.is_active:
            return template

        restored = InvoiceTemplateService().restore(template)
        cache.delete(f"invoice_default_template_{template.document_type}")
        return restored
