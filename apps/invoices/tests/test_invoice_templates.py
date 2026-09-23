from django.test import TestCase

from apps.invoices.models import InvoiceTemplate
from apps.invoices.selectors.invoice_template_selector import InvoiceTemplateSelector
from apps.invoices.services.invoice_template_service import InvoiceTemplateService
from apps.invoices.dto.invoice_template_dto import InvoiceTemplateCreateDTO


class InvoiceTemplateTests(TestCase):
    def test_pos_ticket_document_type_is_available(self):
        self.assertEqual(
            InvoiceTemplate.DocumentType.POS_TICKET,
            "POS_TICKET",
        )
        self.assertIn(
            (
                InvoiceTemplate.DocumentType.POS_TICKET,
                "Ticket POS",
            ),
            InvoiceTemplate.DocumentType.choices,
        )

    def test_create_and_select_default_pos_ticket_template(self):
        template = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="Ticket POS Predeterminado",
                document_type=InvoiceTemplate.DocumentType.POS_TICKET,
                header_content="<div>Mi negocio</div>",
                footer_content="<div>Gracias por su compra</div>",
                is_default=True,
            )
        )

        selected = InvoiceTemplateSelector.get_default_template(
            InvoiceTemplate.DocumentType.POS_TICKET,
        )

        self.assertEqual(selected.pk, template.pk)
        self.assertEqual(selected.document_type, "POS_TICKET")
        self.assertTrue(selected.is_active)
        self.assertTrue(selected.is_default)

    def test_default_template_is_scoped_to_document_type(self):
        purchase_template = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="Compra",
                document_type=InvoiceTemplate.DocumentType.PURCHASE_INVOICE,
                is_default=True,
            )
        )
        sale_template = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="Venta",
                document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
                is_default=True,
            )
        )
        pos_template = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="POS",
                document_type=InvoiceTemplate.DocumentType.POS_TICKET,
                is_default=True,
            )
        )

        self.assertEqual(
            InvoiceTemplateSelector.get_default_template(
                InvoiceTemplate.DocumentType.PURCHASE_INVOICE,
            ).pk,
            purchase_template.pk,
        )
        self.assertEqual(
            InvoiceTemplateSelector.get_default_template(
                InvoiceTemplate.DocumentType.SALE_INVOICE,
            ).pk,
            sale_template.pk,
        )
        self.assertEqual(
            InvoiceTemplateSelector.get_default_template(
                InvoiceTemplate.DocumentType.POS_TICKET,
            ).pk,
            pos_template.pk,
        )

    def test_existing_document_types_remain_available(self):
        self.assertEqual(
            InvoiceTemplate.DocumentType.PURCHASE_INVOICE,
            "PURCHASE_INVOICE",
        )
        self.assertEqual(
            InvoiceTemplate.DocumentType.SALE_INVOICE,
            "SALE_INVOICE",
        )
