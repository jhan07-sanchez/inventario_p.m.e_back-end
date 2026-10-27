from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.configuration.dto import GlobalParameterUpdateDto
from apps.configuration.models import GlobalParameter
from apps.configuration.selectors import GlobalParameterSelector
from apps.configuration.services import GlobalParameterService
from apps.users.models import Role, User, UserRole


class GlobalParameterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="config_admin",
            password="adminpassword123",
            email="config_admin@example.com",
            document_number="12345678",
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
            "/api/v1/auth/login/",
            {"email": "config_admin@example.com", "password": "adminpassword123"},
        )
        # Validación de seguridad recomendada para saber si falló el login
        self.assertEqual(
            login_res.status_code,
            status.HTTP_200_OK,
            f"Error en login: {login_res.data}",
        )
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.parameter = GlobalParameter.objects.create(
            key="DEFAULT_TAX_RATE",
            value="0.19",
            data_type=GlobalParameter.DataType.DECIMAL,
            description="Tasa de IVA",
        )

    def tearDown(self):
        cache.clear()

    def test_selector_get_by_key_caches_result(self):
        self.assertIsNone(cache.get("global_param_DEFAULT_TAX_RATE"))
        param = GlobalParameterSelector.get_by_key("DEFAULT_TAX_RATE")
        self.assertEqual(param.pk, self.parameter.pk)
        self.assertIsNotNone(cache.get("global_param_DEFAULT_TAX_RATE"))

    def test_service_update_invalidates_cache(self):
        GlobalParameterSelector.get_by_key("DEFAULT_TAX_RATE")
        self.assertIsNotNone(cache.get("global_param_DEFAULT_TAX_RATE"))

        dto = GlobalParameterUpdateDto(value="0.21")
        GlobalParameterService.update_parameter(self.parameter, dto)

        # Cache must be invalidated
        self.assertIsNone(cache.get("global_param_DEFAULT_TAX_RATE"))

        refreshed = GlobalParameterSelector.get_by_key("DEFAULT_TAX_RATE")
        self.assertEqual(refreshed.value, "0.21")

    def test_api_create_parameter(self):
        url = reverse("global-parameters-list")
        payload = {
            "key": "CURRENCY",
            "value": "COP",
            "data_type": "STRING",
            "description": "Moneda del sistema",
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["data"]["key"], "CURRENCY")

    def test_get_typed_value_casting(self):
        from decimal import Decimal

        # Decimal
        tax_rate = GlobalParameterService.get_typed_value("DEFAULT_TAX_RATE")
        self.assertEqual(tax_rate, Decimal("0.19"))
        self.assertIsInstance(tax_rate, Decimal)

        # Integer
        GlobalParameter.objects.create(
            key="SESSION_TIMEOUT",
            value="120",
            data_type=GlobalParameter.DataType.INTEGER,
        )
        timeout = GlobalParameterService.get_typed_value("SESSION_TIMEOUT")
        self.assertEqual(timeout, 120)
        self.assertIsInstance(timeout, int)

        # Boolean
        GlobalParameter.objects.create(
            key="ALLOW_NEGATIVE_STOCK",
            value="true",
            data_type=GlobalParameter.DataType.BOOLEAN,
        )
        allow_neg = GlobalParameterService.get_typed_value("ALLOW_NEGATIVE_STOCK")
        self.assertIs(allow_neg, True)

        # Non-existent key returns default
        default_val = GlobalParameterService.get_typed_value(
            "UNKNOWN_PARAM", default="DEFAULT_VALUE"
        )
        self.assertEqual(default_val, "DEFAULT_VALUE")

    def test_validation_rejects_invalid_values_for_data_type(self):
        from django.core.exceptions import ValidationError

        # Invalid INTEGER
        with self.assertRaises(ValidationError):
            GlobalParameterService.validate_value_by_data_type(
                "not_an_int", GlobalParameter.DataType.INTEGER
            )

        # Invalid DECIMAL
        with self.assertRaises(ValidationError):
            GlobalParameterService.validate_value_by_data_type(
                "invalid_decimal", GlobalParameter.DataType.DECIMAL
            )

        # Invalid BOOLEAN
        with self.assertRaises(ValidationError):
            GlobalParameterService.validate_value_by_data_type(
                "maybe", GlobalParameter.DataType.BOOLEAN
            )

    def test_configuration_audit_trail_recorded(self):
        from apps.configuration.models import ConfigurationAudit

        dto = GlobalParameterUpdateDto(value="0.21")
        GlobalParameterService.update_parameter(self.parameter, dto, user=self.user)

        audit = ConfigurationAudit.objects.filter(
            parameter=self.parameter, action=ConfigurationAudit.Action.UPDATE
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.old_value, "0.19")
        self.assertEqual(audit.new_value, "0.21")
        self.assertEqual(audit.user, self.user)

    def test_api_by_key_endpoint(self):
        # Found
        url = reverse("global-parameters-by-key", kwargs={"key": "DEFAULT_TAX_RATE"})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["key"], "DEFAULT_TAX_RATE")

        # Not found
        not_found_url = reverse(
            "global-parameters-by-key", kwargs={"key": "NON_EXISTENT_KEY"}
        )
        res_404 = self.client.get(not_found_url)
        self.assertEqual(res_404.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_catalog_endpoint(self):
        url = reverse("global-parameters-catalog")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("DEFAULT_TAX_RATE", res.data["data"])
        self.assertIn("CURRENCY", res.data["data"])

    def test_api_system_summary_endpoint(self):
        url = reverse("global-parameters-system-summary")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("company_info", res.data["data"])
        self.assertIn("default_templates", res.data["data"])
        self.assertIn("parameters_count", res.data["data"])

    def test_unauthorized_user_cannot_create_parameter(self):
        viewer = User.objects.create_user(
            username="config_viewer",
            password="viewerpassword123",
            email="config_viewer@example.com",
            document_number="87654321",
        )
        viewer_role = Role.objects.create(
            role_name="settings_viewer",
            permissions={"settings.view": True},
        )
        UserRole.objects.create(user=viewer, role=viewer_role)

        viewer_client = APIClient()
        login_res = viewer_client.post(
            "/api/v1/auth/login/",
            {"email": "config_viewer@example.com", "password": "viewerpassword123"},
        )
        token = login_res.data["data"]["access_token"]
        viewer_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # GET parameters is allowed
        res_get = viewer_client.get(reverse("global-parameters-list"))
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)

        # POST is forbidden
        payload = {"key": "HACK", "value": "val", "data_type": "STRING"}
        res_post = viewer_client.post(reverse("global-parameters-list"), payload)
        self.assertEqual(res_post.status_code, status.HTTP_403_FORBIDDEN)
