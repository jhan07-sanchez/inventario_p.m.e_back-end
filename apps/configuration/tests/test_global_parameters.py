from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

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
        print("RESPUESTA DEL SERVIDOR:", res.data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["data"]["key"], "CURRENCY")
