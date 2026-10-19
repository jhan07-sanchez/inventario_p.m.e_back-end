from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.dto.company_info_dto import CompanyInfoUpdateDto
from apps.company_info.models.company_info import CompanyInfo
from apps.company_info.selectors.company_info_selector import CompanyInfoSelector
from apps.company_info.services.company_info_service import CompanyInfoService
from apps.users.models import Role, User, UserRole


class CompanyInfoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="company_admin",
            password="adminpassword123",
            email="comp_admin@example.com",
            document_number="44332211",
        )
        self.role = Role.objects.create(
            role_name="settings_manager",
            permissions={
                "settings.view": True,
                "settings.update": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            reverse("auth-login"),
            {"username": "company_admin", "password": "adminpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.company = CompanyInfo.objects.create(
            business_name="Ferretería P.M.E. S.A.S.",
            trade_name="P.M.E. Ferreterías",
            tax_id="901234567-8",
            phone="6013334455",
            email="info@pme.com",
            is_active=True,
        )

    def tearDown(self):
        cache.clear()

    def test_selector_get_current_caches_result(self):
        self.assertIsNone(cache.get("company_info_current"))
        curr = CompanyInfoSelector.get_current()
        self.assertEqual(curr.pk, self.company.pk)
        self.assertIsNotNone(cache.get("company_info_current"))

    def test_service_update_invalidates_cache(self):
        CompanyInfoSelector.get_current()
        self.assertIsNotNone(cache.get("company_info_current"))

        dto = CompanyInfoUpdateDto(business_name="Ferretería P.M.E. Actualizada")
        CompanyInfoService.update_company_info(self.company, dto)

        # Cache must be invalidated
        self.assertIsNone(cache.get("company_info_current"))

        refreshed = CompanyInfoSelector.get_current()
        self.assertEqual(refreshed.business_name, "Ferretería P.M.E. Actualizada")

    def test_service_remove_logo_invalidates_cache(self):
        CompanyInfoSelector.get_current()
        self.assertIsNotNone(cache.get("company_info_current"))

        CompanyInfoService.remove_logo(self.company)
        self.assertIsNone(cache.get("company_info_current"))

    def test_service_deactivate_and_restore_invalidates_cache(self):
        CompanyInfoSelector.get_current()
        self.assertIsNotNone(cache.get("company_info_current"))

        CompanyInfoService.deactivate_company_info(self.company)
        self.assertIsNone(cache.get("company_info_current"))

        # Since it is inactive, get_current returns None
        curr = CompanyInfoSelector.get_current()
        self.assertIsNone(curr)

        # Restore
        CompanyInfoService.restore_company_info(self.company)
        self.assertIsNone(cache.get("company_info_current"))

        curr2 = CompanyInfoSelector.get_current()
        self.assertIsNotNone(curr2)
        self.assertEqual(curr2.pk, self.company.pk)

    def test_api_current_endpoint(self):
        url = reverse("company-info-current")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["tax_id"], "901234567-8")
