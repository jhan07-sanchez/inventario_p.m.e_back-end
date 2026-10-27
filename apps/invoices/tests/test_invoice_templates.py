from django.test import TestCase

from apps.invoices.dto.invoice_template_dto import InvoiceTemplateCreateDTO
from apps.invoices.models import InvoiceTemplate
from apps.invoices.selectors.invoice_template_selector import InvoiceTemplateSelector
from apps.invoices.services.invoice_template_service import InvoiceTemplateService


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

    def test_create_template_rejects_script_injection(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            InvoiceTemplateService.create_template(
                InvoiceTemplateCreateDTO(
                    name="Plantilla Maliciosa",
                    document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
                    header_content="<script>alert('xss')</script>",
                )
            )
        self.assertIn("código ejecutable o etiquetas no permitidas", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx2:
            InvoiceTemplateService.create_template(
                InvoiceTemplateCreateDTO(
                    name="Plantilla con evento malicioso",
                    document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
                    body_content="<img src='invalid.jpg' onerror='exploit()'>",
                )
            )
        self.assertIn(
            "código ejecutable o etiquetas no permitidas", str(ctx2.exception)
        )

    def test_create_template_rejects_unbalanced_loop_tags(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            InvoiceTemplateService.create_template(
                InvoiceTemplateCreateDTO(
                    name="Bucle Desbalanceado",
                    document_type=InvoiceTemplate.DocumentType.POS_TICKET,
                    body_content="<div>{{#items}}<span>{{item_name}}</span></div>",
                )
            )
        self.assertIn("no están balanceadas", str(ctx.exception))

    def test_create_template_rejects_unknown_variables(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            InvoiceTemplateService.create_template(
                InvoiceTemplateCreateDTO(
                    name="Variable Desconocida",
                    document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
                    header_content="<div>{{ variable_totalmente_invalida }}</div>",
                )
            )
        self.assertIn("Variable no permitida o desconocida", str(ctx.exception))

    def test_preview_template_renders_successfully(self):
        from apps.company_info.models import CompanyInfo

        CompanyInfo.objects.all().delete()
        CompanyInfo.objects.create(
            business_name="Ferretería Demo S.A.S.",
            tax_id="800111222-3",
            phone="6018889900",
            address="Calle 100 # 15-20",
            email="contacto@ferreteriademo.com",
            city="Bogotá",
            receipt_footer="Gracias por su fidelidad.",
            is_active=True,
        )

        template = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="Plantilla Vista Previa",
                document_type=InvoiceTemplate.DocumentType.POS_TICKET,
                header_content="<h1>{{ company_name }}</h1><p>{{ company_tax_id }}</p>",
                body_content="<div>Doc: {{ document_number }}</div><ul>{{#items}}<li>{{ item_name }} - {{ item_price }}</li>{{/items}}</ul>",
                footer_content="<p>{{ company_receipt_footer }}</p>",
            )
        )

        preview = InvoiceTemplateService.preview_template(template)
        self.assertEqual(preview["template_id"], template.pk)
        self.assertIn("Ferretería Demo S.A.S.", preview["rendered_header"])
        self.assertIn("800111222-3", preview["rendered_header"])
        self.assertIn("Doc: FAC-000001", preview["rendered_body"])
        self.assertIn("Tornillo Drywall", preview["rendered_body"])
        self.assertIn("Gracias por su fidelidad.", preview["rendered_footer"])

    def test_set_default_method(self):
        t1 = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="T1",
                document_type=InvoiceTemplate.DocumentType.POS_TICKET,
                is_default=True,
            )
        )
        t2 = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="T2",
                document_type=InvoiceTemplate.DocumentType.POS_TICKET,
                is_default=False,
            )
        )

        # Set t2 as default
        InvoiceTemplateService.set_default(t2)

        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertFalse(t1.is_default)
        self.assertTrue(t2.is_default)

    def test_historical_invoice_preserves_company_snapshot_when_company_updates(self):
        from decimal import Decimal

        from django.utils import timezone

        from apps.company_info.models import CompanyInfo
        from apps.invoices.models import Invoice
        from apps.sales.models import Sale

        CompanyInfo.objects.all().delete()
        company = CompanyInfo.objects.create(
            business_name="Nombre Corporativo Histórico",
            tax_id="900000001-1",
            phone="3001234567",
            email="historico@empresa.com",
            address="Av 1 # 2-3",
            city="Medellín",
            receipt_footer="Pie original",
            is_active=True,
        )

        template = InvoiceTemplateService.create_template(
            InvoiceTemplateCreateDTO(
                name="Factura Estándar",
                document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
                is_default=True,
            )
        )

        from apps.users.models import User

        user = User.objects.create_user(
            username="sale_user_hist",
            password="password123",
            email="sale_user_hist@example.com",
            document_number="77889900",
        )

        sale = Sale.objects.create(
            sale_number="VEN-009999",
            user=user,
            subtotal=Decimal("1000.00"),
            total=Decimal("1000.00"),
            status=Sale.SaleStatus.COMPLETED,
        )

        # Invoice takes snapshot of current company
        invoice = Invoice.objects.create(
            invoice_number="FAC-HIST-001",
            document_type=Invoice.DocumentType.SALE_INVOICE,
            template=template,
            sale=sale,
            issue_date=timezone.now().date(),
            subtotal=Decimal("1000.00"),
            total=Decimal("1000.00"),
            company_name_snapshot=company.business_name,
            company_tax_id_snapshot=company.tax_id,
            company_address_snapshot=company.address,
            company_phone_snapshot=company.phone,
            company_email_snapshot=company.email,
            company_city_snapshot=company.city,
            company_receipt_footer_snapshot=company.receipt_footer,
        )

        # Now company changes its name, tax_id, and address
        company.business_name = "Nueva Razón Social 2026"
        company.tax_id = "999999999-9"
        company.address = "Calle Nueva 500"
        company.save()

        # The historical invoice snapshot must remain unchanged
        invoice.refresh_from_db()
        self.assertEqual(invoice.company_name_snapshot, "Nombre Corporativo Histórico")
        self.assertEqual(invoice.company_tax_id_snapshot, "900000001-1")
        self.assertEqual(invoice.company_address_snapshot, "Av 1 # 2-3")
