from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from apps.company_info.models import CompanyInfo
from apps.core.models.tenant_model import TenantModel
from apps.core.selectors.tenant_selector import TenantSelector
from apps.core.services.tenant_service import TenantService
from apps.core.views.base_viewset import BaseViewSet
from apps.finance.models.financial_account import FinancialAccount
from apps.users.models import User


class TenantIsolationEngineTests(TestCase):
    """
    Pruebas unitarias para el motor base de aislamiento multi-tenant
    (TenantModel, TenantSelector, TenantService y BaseViewSet).
    """

    def setUp(self):
        self.factory = RequestFactory()

        self.company_a = CompanyInfo.objects.create(
            business_name="Empresa A SAS",
            trade_name="Empresa A",
            tax_id="111-A",
            is_active=True,
        )

        self.company_b = CompanyInfo.objects.create(
            business_name="Empresa B Ltda",
            trade_name="Empresa B",
            tax_id="222-B",
            is_active=True,
        )

        self.user = User.objects.create_user(
            username="test_tenant_user",
            email="tenant_user@example.com",
            password="Password123!",
            document_number="55443322",
        )

        # FinancialAccount es un modelo existente que ya posee relación 'company'
        self.account_a = FinancialAccount.objects.create(
            name="Caja Principal A",
            account_type=FinancialAccount.AccountType.CASH,
            company=self.company_a,
            is_active=True,
        )

        self.account_b = FinancialAccount.objects.create(
            name="Caja Principal B",
            account_type=FinancialAccount.AccountType.CASH,
            company=self.company_b,
            is_active=True,
        )

    def test_tenant_selector_isolates_records_by_company(self):
        selector = TenantSelector(FinancialAccount)

        # Consultar para Empresa A
        results_a = selector.get_for_company(self.company_a)
        self.assertEqual(results_a.count(), 1)
        self.assertEqual(results_a.first().name, "Caja Principal A")

        # Consultar para Empresa B
        results_b = selector.get_for_company(self.company_b)
        self.assertEqual(results_b.count(), 1)
        self.assertEqual(results_b.first().name, "Caja Principal B")

    def test_tenant_selector_prevents_idor(self):
        selector = TenantSelector(FinancialAccount)

        # Intentar acceder al ID de la Empresa B desde el contexto de la Empresa A
        record = selector.get_by_id_for_company(
            record_id=self.account_b.pk, company=self.company_a
        )
        self.assertIsNone(record)

        # Acceder con la empresa correcta sí retorna el registro
        valid_record = selector.get_by_id_for_company(
            record_id=self.account_b.pk, company=self.company_b
        )
        self.assertIsNotNone(valid_record)
        self.assertEqual(valid_record.pk, self.account_b.pk)

    def test_tenant_service_cross_tenant_validation_rejects_foreign_entity(self):
        service = TenantService(FinancialAccount)

        class DummyEntity:
            company_id = self.company_b.id_company

        # Intentar asociar una entidad de Empresa B en operación para Empresa A
        with self.assertRaises(ValidationError) as ctx:
            service.validate_cross_tenant_integrity(
                {"related_item": DummyEntity()}, company=self.company_a
            )
        self.assertIn("pertenece a otra empresa", str(ctx.exception))

    def test_base_viewset_get_queryset_scopes_to_request_company(self):
        class DummyViewSet(BaseViewSet):
            queryset = FinancialAccount.objects.all()

        view = DummyViewSet()
        req = self.factory.get("/")
        req.user = self.user
        req.company = self.company_a
        view.request = req

        scoped_qs = view.get_queryset()
        self.assertEqual(scoped_qs.count(), 1)
        self.assertEqual(scoped_qs.first().company_id, self.company_a.id_company)

