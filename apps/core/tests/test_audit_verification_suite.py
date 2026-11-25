from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import Http404
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import PermissionDenied

from apps.cash.models.payment import Payment
from apps.categories.models import Category
from apps.company_info.models import CompanyInfo
from apps.configuration.views.configuration_audit_viewset import (
    ConfigurationAuditViewSet,
)
from apps.core.context import set_current_company_id
from apps.core.enums import PaymentMethod
from apps.core.views.base_viewset import BaseReadOnlyViewSet, BaseViewSet
from apps.products.models import Product
from apps.purchases.dto.purchase_dto import (
    PurchaseCreateDTO,
    PurchaseDetailCreateDTO,
    PurchasePayDTO,
)
from apps.purchases.models import Purchase
from apps.purchases.selectors.purchase_selector import PurchaseSelector
from apps.purchases.services.purchase_payment_service import (
    PurchasePaymentService,
)
from apps.purchases.services.purchase_service import PurchaseService
from apps.suppliers.models import Supplier
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class AuditVerificationSuite(TestCase):
    """
    Suite de verificación post-implementación para auditar:
    - H-01 & H-07: Aislamiento Fail-Closed en BaseViewSet y ausencia de company_id == 1.
    - H-02: Colisión de prefijos en pagos de compras.
    - H-03: Inyección de proveedores cross-tenant.
    - H-10: Inmutabilidad de TenantModel y from_db().
    """

    def setUp(self):
        set_current_company_id(None)
        self.c1 = CompanyInfo.objects.create(
            business_name="Empresa A", tax_id="900000001-1"
        )
        self.c2 = CompanyInfo.objects.create(
            business_name="Empresa B", tax_id="900000002-2"
        )

        self.user_multi = User.objects.create_user(
            username="multi_user",
            email="multi@test.com",
            password="Password123!",
            document_number="1001",
        )
        self.role = Role.objects.create(
            role_name="admin_role",
            permissions={
                "products.view": True,
                "products.create": True,
                "purchases.create": True,
            },
        )
        CompanyMembership.objects.create(
            user=self.user_multi,
            company=self.c1,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        CompanyMembership.objects.create(
            user=self.user_multi,
            company=self.c2,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        self.cat1 = Category.objects.create(name="Cat 1", company=self.c1)
        self.cat2 = Category.objects.create(name="Cat 2", company=self.c2)
        self.p1 = Product.objects.create(
            name="Prod C1",
            code="P1",
            company=self.c1,
            category=self.cat1,
            purchase_price=Decimal("10"),
            sale_price=Decimal("20"),
        )
        self.p2 = Product.objects.create(
            name="Prod C2",
            code="P2",
            company=self.c2,
            category=self.cat2,
            purchase_price=Decimal("10"),
            sale_price=Decimal("20"),
        )
        self.rf = RequestFactory()

    def tearDown(self):
        set_current_company_id(None)
        super().tearDown()

    def test_h01_and_h07_fail_closed_multi_tenant_isolation(self):
        """Verifica que un usuario multi-empresa sin X-Company-ID sea rechazado (Fail-Closed)"""

        class DummyProductViewSet(BaseViewSet):
            queryset = Product.objects.all()

        viewset = DummyProductViewSet()

        # 1. Sin header X-Company-ID -> debe lanzar PermissionDenied
        req_no_header = self.rf.get("/api/v1/products/")
        req_no_header.user = self.user_multi
        viewset.request = req_no_header

        with self.assertRaises(PermissionDenied):
            viewset.get_queryset()

        # 2. Con header C1 -> solo ve p1
        req_c1 = self.rf.get("/api/v1/products/", HTTP_X_COMPANY_ID=str(self.c1.pk))
        req_c1.user = self.user_multi
        viewset.request = req_c1
        qs_c1 = viewset.get_queryset()
        p_ids_1 = list(qs_c1.values_list("id_product", flat=True))
        self.assertIn(self.p1.pk, p_ids_1)
        self.assertNotIn(self.p2.pk, p_ids_1)

        # 3. Con header C2 -> solo ve p2
        req_c2 = self.rf.get("/api/v1/products/", HTTP_X_COMPANY_ID=str(self.c2.pk))
        req_c2.user = self.user_multi
        viewset.request = req_c2
        qs_c2 = viewset.get_queryset()
        p_ids_2 = list(qs_c2.values_list("id_product", flat=True))
        self.assertIn(self.p2.pk, p_ids_2)
        self.assertNotIn(self.p1.pk, p_ids_2)

    def test_h03_cross_tenant_injection_in_purchases_blocked(self):
        """Verifica que no se pueda usar un proveedor de C2 en una compra de C1"""
        sup_c2 = Supplier.objects.create(
            business_name="Proveedor C2",
            document_number="SUP-C2",
            company=self.c2,
        )

        dto_malicious = PurchaseCreateDTO(
            supplier_id=sup_c2.pk,
            issue_date=None,
            notes=None,
            company_id=self.c1.pk,
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.p1.pk,
                    quantity=Decimal("5"),
                    unit_price=Decimal("10"),
                )
            ],
        )

        with self.assertRaises(ValidationError) as ctx:
            PurchaseService.create_purchase(dto_malicious)
        self.assertIn("pertenece a otra empresa", str(ctx.exception))

    def test_h02_purchase_payment_collision_prevention(self):
        """Verifica que pagos de compras con números similares (ej. #1 y #10) no colisionen"""
        sup_c1 = Supplier.objects.create(
            business_name="Proveedor C1",
            document_number="SUP-C1",
            company=self.c1,
        )
        dto_pur = PurchaseCreateDTO(
            supplier_id=sup_c1.pk,
            issue_date=None,
            notes=None,
            company_id=self.c1.pk,
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.p1.pk,
                    quantity=Decimal("10"),
                    unit_price=Decimal("100"),
                )
            ],
        )
        pur = PurchaseService.create_purchase(dto_pur)
        pur.status = Purchase.Status.COMPLETED
        pur.save(update_fields=["status"])

        # Pagar $300 a esta compra
        pay_dto = PurchasePayDTO(
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.TRANSFER,
            reference="TRF-001",
        )
        PurchasePaymentService.pay_purchase(
            purchase_id=pur.pk, dto=pay_dto, user=self.user_multi
        )

        # Crear un pago falso para otra compra con número que empieza igual (ej: #{pur.pk}0)
        Payment.objects.create(
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.TRANSFER,
            status=Payment.PaymentStatus.COMPLETED,
            reference=f"COMPRA #{pur.pk}0 - PAGO DE OTRA COMPRA",
        )

        # Consultar total pagado con el filtro estricto
        paid_total = Payment.objects.filter(
            PurchaseSelector.get_purchase_payment_filter(pur.pk),
            status=Payment.PaymentStatus.COMPLETED,
            is_active=True,
        ).aggregate(total=Sum("amount"))["total"]

        # Debe ser exactamente $300, NUNCA $800
        self.assertEqual(paid_total, Decimal("300.00"))

    def test_purchase_cancellation_with_payments_blocked(self):
        """Verifica que no se pueda cancelar una compra con pagos completados registrados"""
        sup_c1 = Supplier.objects.create(
            business_name="Proveedor Anulacion",
            document_number="SUP-ANUL",
            company=self.c1,
        )
        dto_pur = PurchaseCreateDTO(
            supplier_id=sup_c1.pk,
            issue_date=None,
            notes=None,
            company_id=self.c1.pk,
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.p1.pk,
                    quantity=Decimal("5"),
                    unit_price=Decimal("50"),
                )
            ],
        )
        pur = PurchaseService.create_purchase(dto_pur)
        pur.status = Purchase.Status.PENDING
        pur.save(update_fields=["status"])

        # Pagar $100
        pay_dto = PurchasePayDTO(
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.TRANSFER,
            reference="TRF-ANUL-1",
        )
        PurchasePaymentService.pay_purchase(
            purchase_id=pur.pk, dto=pay_dto, user=self.user_multi
        )

        # Intentar cancelar la compra -> debe fallar
        with self.assertRaises(ValidationError) as ctx:
            PurchaseService.cancel_purchase(pur)
        self.assertIn(
            "No se puede cancelar una compra que tiene pagos registrados",
            str(ctx.exception),
        )

        # Si el pago es anulado, entonces la compra sí puede cancelarse
        Payment.objects.filter(
            PurchaseSelector.get_purchase_payment_filter(pur.pk)
        ).update(status=Payment.PaymentStatus.CANCELLED)

        pur_cancelled = PurchaseService.cancel_purchase(pur)
        self.assertEqual(pur_cancelled.status, Purchase.Status.CANCELLED)

    def test_h10_tenant_model_immutability_and_from_db(self):
        """Verifica que TenantModel impida reasignar la empresa en save()"""
        prod = Product.objects.get(pk=self.p1.pk)
        self.assertEqual(getattr(prod, "_loaded_company_id", None), self.c1.pk)

        # Intentar reasignar a C2
        prod.company = self.c2
        with self.assertRaises(ValidationError) as ctx:
            prod.save()
        self.assertIn("No está permitido transferir o reasignar", str(ctx.exception))

    def test_single_membership_user_auto_resolution(self):
        """Verifica que un usuario con una sola membresía resuelva su empresa automáticamente"""
        user_single = User.objects.create_user(
            username="single_user",
            email="single@test.com",
            password="Password123!",
            document_number="1002",
        )
        CompanyMembership.objects.create(
            user=user_single,
            company=self.c1,
            role=self.role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        class DummyProductViewSet(BaseViewSet):
            queryset = Product.objects.all()

        viewset = DummyProductViewSet()
        req = self.rf.get("/api/v1/products/")
        req.user = user_single
        viewset.request = req

        qs = viewset.get_queryset()
        p_ids = list(qs.values_list("id_product", flat=True))
        self.assertIn(self.p1.pk, p_ids)
        self.assertNotIn(self.p2.pk, p_ids)

    def test_h12_configuration_audit_viewset_inheritance(self):
        """Verifica que ConfigurationAuditViewSet hereda de BaseReadOnlyViewSet y no permite escrituras"""
        self.assertTrue(issubclass(ConfigurationAuditViewSet, BaseReadOnlyViewSet))

    def test_h04_perform_create_rejects_missing_company(self):
        """Verifica que perform_create rechace la creación sin una empresa activa identificada"""

        class DummyProductViewSet(BaseViewSet):
            queryset = Product.objects.all()

        viewset = DummyProductViewSet()
        req = self.rf.post("/api/v1/products/")
        req.user = self.user_multi
        viewset.request = req

        class DummySerializer:
            def save(self, **kwargs):
                pass

        with self.assertRaises(PermissionDenied) as ctx:
            viewset.perform_create(DummySerializer())
        self.assertIn("Se requiere un contexto de empresa activa", str(ctx.exception))

    def test_cross_tenant_get_object_returns_404(self):
        """Verifica que intentar obtener un objeto de otra empresa mediante el ViewSet devuelva 404"""

        class DummyProductViewSet(BaseViewSet):
            queryset = Product.objects.all()
            lookup_field = "pk"

        viewset = DummyProductViewSet()
        viewset.kwargs = {"pk": self.p2.pk}  # p2 pertenece a c2

        # Petición enviando X-Company-ID = c1
        req = self.rf.get(
            f"/api/v1/products/{self.p2.pk}/", HTTP_X_COMPANY_ID=str(self.c1.pk)
        )
        req.user = self.user_multi
        viewset.request = req

        with self.assertRaises(Http404):
            viewset.get_object()

    def test_h02_partial_and_full_payment_lifecycle(self):
        """Verifica ciclo contable completo de pagos: parciales, total y rechazo de sobrepago"""
        sup_c1 = Supplier.objects.create(
            business_name="Proveedor Pagos",
            document_number="SUP-PAY",
            company=self.c1,
        )
        dto_pur = PurchaseCreateDTO(
            supplier_id=sup_c1.pk,
            issue_date=None,
            notes=None,
            company_id=self.c1.pk,
            details=[
                PurchaseDetailCreateDTO(
                    product_id=self.p1.pk,
                    quantity=Decimal("10"),
                    unit_price=Decimal("100"),
                )
            ],
        )
        pur = PurchaseService.create_purchase(dto_pur)
        pur.status = Purchase.Status.COMPLETED
        pur.save(update_fields=["status"])

        # Pago 1: $300 (parcial)
        res1 = PurchasePaymentService.pay_purchase(
            purchase_id=pur.pk,
            dto=PurchasePayDTO(
                amount=Decimal("300.00"),
                payment_method=PaymentMethod.TRANSFER,
                reference="P1",
            ),
            user=self.user_multi,
        )
        self.assertEqual(Decimal(res1["total_paid"]), Decimal("300.00"))
        self.assertEqual(Decimal(res1["pending_balance"]), Decimal("700.00"))
        self.assertFalse(res1["is_fully_paid"])

        # Pago 2: $700 (completa la compra)
        res2 = PurchasePaymentService.pay_purchase(
            purchase_id=pur.pk,
            dto=PurchasePayDTO(
                amount=Decimal("700.00"),
                payment_method=PaymentMethod.TRANSFER,
                reference="P2",
            ),
            user=self.user_multi,
        )
        self.assertEqual(Decimal(res2["total_paid"]), Decimal("1000.00"))
        self.assertEqual(Decimal(res2["pending_balance"]), Decimal("0.00"))
        self.assertTrue(res2["is_fully_paid"])

        # Pago 3: intento de pagar $1 más -> debe fallar por saldo excedido
        with self.assertRaises(ValidationError) as ctx:
            PurchasePaymentService.pay_purchase(
                purchase_id=pur.pk,
                dto=PurchasePayDTO(
                    amount=Decimal("1.00"),
                    payment_method=PaymentMethod.TRANSFER,
                    reference="P3-EXCESS",
                ),
                user=self.user_multi,
            )
        self.assertIn("supera el saldo pendiente", str(ctx.exception))

    def test_tenant_isolation_update_and_delete_protection(self):
        """Verifica que una empresa no pueda modificar ni eliminar registros de otra"""

        class DummyProductViewSet(BaseViewSet):
            queryset = Product.objects.all()
            lookup_field = "pk"

        viewset = DummyProductViewSet()
        viewset.kwargs = {"pk": self.p2.pk}  # p2 es de c2

        # Petición enviando X-Company-ID = c1 para modificar p2
        req_update = self.rf.patch(
            f"/api/v1/products/{self.p2.pk}/",
            data={"name": "Modificado Ilegalmente"},
            content_type="application/json",
            HTTP_X_COMPANY_ID=str(self.c1.pk),
        )
        req_update.user = self.user_multi
        viewset.request = req_update

        with self.assertRaises(Http404):
            viewset.get_object()

        # Petición enviando X-Company-ID = c1 para eliminar p2
        req_delete = self.rf.delete(
            f"/api/v1/products/{self.p2.pk}/",
            HTTP_X_COMPANY_ID=str(self.c1.pk),
        )
        req_delete.user = self.user_multi
        viewset.request = req_delete

        with self.assertRaises(Http404):
            viewset.get_object()

    def test_null_company_records_isolated(self):
        """Verifica que registros con company=NULL sean rechazados por la restricción NOT NULL de base de datos"""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Product.objects.bulk_create(
                [
                    Product(
                        name="Orphan Product",
                        code="ORPHAN",
                        company=None,
                        category=self.cat1,
                        purchase_price=Decimal("5"),
                        sale_price=Decimal("10"),
                    )
                ]
            )

    def test_serializer_company_tampering_protection(self):
        """Verifica que BaseViewSet inyecte la empresa del contexto e ignore manipulación en serializer"""

        class DummySerializer:
            Meta = type("Meta", (), {"model": Product})

            def __init__(self):
                self.saved_kwargs = None

            def save(self, **kwargs):
                self.saved_kwargs = kwargs

        class DummyProductViewSet(BaseViewSet):
            queryset = Product.objects.all()

        viewset = DummyProductViewSet()
        req = self.rf.post("/api/v1/products/", HTTP_X_COMPANY_ID=str(self.c1.pk))
        req.user = self.user_multi
        viewset.request = req

        ser = DummySerializer()
        viewset.perform_create(ser)
        self.assertEqual(ser.saved_kwargs.get("company_id"), self.c1.pk)
