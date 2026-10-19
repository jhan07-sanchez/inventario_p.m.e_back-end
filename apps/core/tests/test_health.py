from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_root_health_check_returns_200(self):
        """El endpoint raíz /health/ debe responder 200 con estado healthy."""
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "healthy")
        self.assertIn("cache", data)

    def test_api_health_check_returns_200(self):
        """El endpoint /api/v1/health/ debe responder 200 sin requerir autenticación."""
        response = self.client.get(reverse("api-health-check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "healthy")

    @patch("apps.core.views.health_view.connection.cursor")
    def test_health_check_db_failure_returns_503(self, mock_cursor):
        """Si la conexión a la base de datos falla, debe responder 503 con status unhealthy."""
        mock_cursor.side_effect = Exception("Simulated connection timeout")

        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertEqual(data.get("status"), "unhealthy")
        self.assertEqual(data.get("database"), "unhealthy")
