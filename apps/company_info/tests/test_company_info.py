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
        if hasattr(self, "company"):
            try:
                self.company.refresh_from_db()
                if self.company.logo:
                    self.company.logo.delete(save=False)
            except Exception:
                pass

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

    def test_singleton_creation_rejected_when_company_already_exists(self):
        from django.core.exceptions import ValidationError

        from apps.company_info.dto.company_info_dto import CompanyInfoCreateDto

        dto = CompanyInfoCreateDto(
            business_name="Segunda Empresa S.A.",
            tax_id="999888777-1",
        )
        with self.assertRaises(ValidationError) as ctx:
            CompanyInfoService.create_company_info(dto)
        self.assertIn("Ya existe una empresa configurada", str(ctx.exception))

    def test_upload_logo_validation_rejects_invalid_file_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake_exe = SimpleUploadedFile(
            "malware.exe",
            b"MZ\x90\x00\x03\x00\x00\x00",
            content_type="application/x-msdownload",
        )
        url = reverse("company-info-upload-logo", kwargs={"pk": self.company.pk})
        res = self.client.post(url, {"logo": fake_exe}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data["success"])

    def test_upload_logo_validation_rejects_oversized_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # 3 MB file (exceeds 2 MB limit)
        oversized = SimpleUploadedFile(
            "huge_logo.png", b"0" * (3 * 1024 * 1024), content_type="image/png"
        )
        url = reverse("company-info-upload-logo", kwargs={"pk": self.company.pk})
        res = self.client.post(url, {"logo": oversized}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data["success"])

    def test_upload_logo_success_with_valid_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Minimal 1x1 transparent PNG
        valid_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
            b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        logo = SimpleUploadedFile("logo_pme.png", valid_png, content_type="image/png")
        url = reverse("company-info-upload-logo", kwargs={"pk": self.company.pk})
        res = self.client.post(url, {"logo": logo}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])

        self.company.refresh_from_db()
        if self.company.logo:
            self.company.logo.delete(save=False)

    def test_unauthorized_user_cannot_update_company_info(self):
        # Create viewer user without update permission
        viewer = User.objects.create_user(
            username="company_viewer",
            password="viewerpassword123",
            email="viewer@example.com",
            document_number="99887766",
        )
        viewer_role = Role.objects.create(
            role_name="settings_viewer",
            permissions={"settings.view": True},
        )
        UserRole.objects.create(user=viewer, role=viewer_role)

        viewer_client = APIClient()
        login_res = viewer_client.post(
            reverse("auth-login"),
            {"username": "company_viewer", "password": "viewerpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        viewer_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # GET current works for viewer
        curr_res = viewer_client.get(reverse("company-info-current"))
        self.assertEqual(curr_res.status_code, status.HTTP_200_OK)

        # PATCH fails with 403 Forbidden
        update_url = reverse("company-info-detail", kwargs={"pk": self.company.pk})
        patch_res = viewer_client.patch(update_url, {"trade_name": "Nuevo Nombre"})
        self.assertEqual(patch_res.status_code, status.HTTP_403_FORBIDDEN)
