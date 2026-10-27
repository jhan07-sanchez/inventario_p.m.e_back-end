from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.invoices.dto.invoice_dto import InvoiceCreateDTO, InvoiceItemCreateDTO
from apps.invoices.models import Invoice, InvoiceTemplate
from apps.invoices.selectors.invoice_selector import InvoiceSelector
from apps.invoices.selectors.invoice_template_selector import InvoiceTemplateSelector
from apps.invoices.services.invoice_service import InvoiceService
from apps.invoices.services.invoice_template_service import InvoiceTemplateService
from apps.products.models import Product
from apps.sales.models import Sale
from apps.users.models import Role, User, UserRole


class InvoiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="invoice_admin",
            password="adminpassword123",
            email="inv_admin@example.com",
            document_number="98765432",
        )
        self.role = Role.objects.create(
            role_name="invoice_manager",
            permissions={
                "invoices.view": True,
                "invoices.create": True,
                "invoices.update": True,
                "invoices.delete": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "invoice_admin", "password": "adminpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.category = Category.objects.create(name="Papelería", is_active=True)
        self.product1 = Product.objects.create(
            code="PAP-001",
            name="Cuaderno 100 Hojas",
            category=self.category,
            purchase_price=Decimal("2.00"),
            sale_price=Decimal("4.00"),
        )
        self.product2 = Product.objects.create(
            code="PAP-002",
            name="Bolígrafo Negro",
            category=self.category,
            purchase_price=Decimal("0.50"),
            sale_price=Decimal("1.20"),
        )

        self.sale = Sale.objects.create(
            sale_number="VEN-00001",
            user=self.user,
            subtotal=Decimal("5.20"),
            total=Decimal("5.20"),
            status=Sale.SaleStatus.COMPLETED,
        )

        self.template = InvoiceTemplate.objects.create(
            name="Plantilla Ticket POS",
            document_type=InvoiceTemplate.DocumentType.POS_TICKET,
            is_default=True,
            is_active=True,
        )

    def tearDown(self):
        cache.clear()

    def test_create_pos_ticket_from_sale(self):
        """
        Demuestra la corrección del defecto de validación en _resolve_origin:
        Las ventas ahora pueden generar tickets POS sin ValidationError.
        """
        dto = InvoiceCreateDTO(
            document_type=Invoice.DocumentType.POS_TICKET,
            template_id=self.template.pk,
            invoice_number="TICK-00001",
            sale_id=self.sale.pk,
            items=[
                InvoiceItemCreateDTO(
                    product_id=self.product1.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("4.00"),
                ),
                InvoiceItemCreateDTO(
                    product_id=self.product2.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("1.20"),
                ),
            ],
        )

        invoice = InvoiceService.create_invoice(dto)
        self.assertIsNotNone(invoice.pk)
        self.assertEqual(invoice.document_type, Invoice.DocumentType.POS_TICKET)
        self.assertEqual(invoice.sale_id, self.sale.pk)
        self.assertEqual(invoice.items.count(), 2)
        self.assertEqual(invoice.total, Decimal("5.20"))

    def test_invoice_soft_delete_and_restore(self):
        dto = InvoiceCreateDTO(
            document_type=Invoice.DocumentType.POS_TICKET,
            template_id=self.template.pk,
            invoice_number="TICK-00002",
            sale_id=self.sale.pk,
            items=[
                InvoiceItemCreateDTO(
                    product_id=self.product1.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("4.00"),
                )
            ],
        )
        invoice = InvoiceService.create_invoice(dto)

        # Soft delete
        InvoiceService.deactivate_invoice(invoice)
        invoice.refresh_from_db()
        self.assertFalse(invoice.is_active)

        # Base get_by_id raises 404 without include_deleted
        with self.assertRaises(Exception):
            InvoiceSelector.get_by_id(invoice.pk, include_deleted=False)

        # Base get_by_id succeeds with include_deleted=True
        found = InvoiceSelector.get_by_id(invoice.pk, include_deleted=True)
        self.assertEqual(found.pk, invoice.pk)

        # Restore
        InvoiceService.restore_invoice(found)
        found.refresh_from_db()
        self.assertTrue(found.is_active)
        self.assertIsNone(found.deleted_at)

    def test_invoice_api_restore_endpoint(self):
        dto = InvoiceCreateDTO(
            document_type=Invoice.DocumentType.POS_TICKET,
            template_id=self.template.pk,
            invoice_number="TICK-00003",
            sale_id=self.sale.pk,
            items=[
                InvoiceItemCreateDTO(
                    product_id=self.product1.pk,
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("4.00"),
                )
            ],
        )
        invoice = InvoiceService.create_invoice(dto)

        delete_url = reverse("invoices-detail", kwargs={"pk": invoice.pk})
        restore_url = reverse("invoices-restore", kwargs={"pk": invoice.pk})

        del_res = self.client.delete(delete_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        invoice.refresh_from_db()
        self.assertFalse(invoice.is_active)

        rest_res = self.client.post(restore_url)
        self.assertEqual(rest_res.status_code, status.HTTP_200_OK)
        self.assertEqual(rest_res.data["code"], "INVOICE_RESTORED")

        invoice.refresh_from_db()
        self.assertTrue(invoice.is_active)
        self.assertIsNone(invoice.deleted_at)

    def test_template_cache_invalidation_on_deactivate_and_restore(self):
        cache_key = f"invoice_default_template_{self.template.document_type}"

        # Fetch and warm cache
        selected = InvoiceTemplateSelector.get_default_template(
            self.template.document_type
        )
        self.assertEqual(selected.pk, self.template.pk)
        self.assertIsNotNone(cache.get(cache_key))

        # Deactivate must invalidate cache
        InvoiceTemplateService.deactivate_template(self.template)
        self.assertIsNone(cache.get(cache_key))

        # Restore must invalidate cache
        InvoiceTemplateService.restore_template(self.template)
        self.assertIsNone(cache.get(cache_key))
