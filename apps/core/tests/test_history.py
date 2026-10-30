from rest_framework import status
from rest_framework.test import APITestCase

from apps.configuration.models import ConfigurationAudit, GlobalParameter
from apps.users.models import Role, User, UserRole


class SystemHistoryViewSetTests(APITestCase):
    def setUp(self):
        # Create test user with permissions
        self.user = User.objects.create_user(
            username="history_admin",
            password="adminpassword123",
            email="history_admin@example.com",
            document_number="99887766",
        )
        self.role = Role.objects.create(
            role_name="history_viewer",
            permissions={
                "settings.view": True,
            },
        )
        UserRole.objects.create(user=self.user, role=self.role)

        login_res = self.client.post(
            "/api/v1/auth/login/",
            {"email": "history_admin@example.com", "password": "adminpassword123"},
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        token = login_res.data["data"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_missing_model_param_returns_400(self):
        res = self.client.get("/api/v1/history/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["code"], "VALIDATION_ERROR")

    def test_unregistered_model_returns_404(self):
        res = self.client.get("/api/v1/history/?model=non_existent_model")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["code"], "NOT_FOUND")

    def test_history_user_model_list(self):
        res = self.client.get("/api/v1/history/?model=user")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["code"], "SUCCESS")
        results = res.data["data"]["results"]
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)

        # Verify contract keys
        first = results[0]
        self.assertIn("history_id", first)
        self.assertIn("history_date", first)
        self.assertIn("history_user", first)
        self.assertIn("action", first)
        self.assertIn("object_repr", first)
        self.assertIn("changes", first)

    def test_history_user_model_filter_by_object_id(self):
        # Using custom primary key id_user
        res = self.client.get(f"/api/v1/history/?model=user&object_id={self.user.id_user}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["code"], "SUCCESS")
        results = res.data["data"]["results"]
        self.assertGreaterEqual(len(results), 1)
        for item in results:
            self.assertIn(self.user.username, item["object_repr"])

    def test_history_parameter_delegation_to_configuration_audit(self):
        param = GlobalParameter.objects.create(
            key="TEST_HIST_KEY",
            value="10",
            data_type="INTEGER",
        )
        ConfigurationAudit.objects.create(
            parameter=param,
            parameter_key=param.key,
            action=ConfigurationAudit.Action.UPDATE,
            user=self.user,
            old_value="10",
            new_value="20",
            reason="Test update for history",
        )

        res = self.client.get("/api/v1/history/?model=parameter")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["code"], "SUCCESS")
        results = res.data["data"]["results"]
        self.assertGreaterEqual(len(results), 1)

        match = next((item for item in results if item["object_repr"] == "TEST_HIST_KEY"), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["history_user"], "history_admin")
        self.assertEqual(len(match["changes"]), 1)
        self.assertEqual(match["changes"][0]["old"], "10")
        self.assertEqual(match["changes"][0]["new"], "20")

    def test_history_sensitive_fields_masked(self):
        # Update user password
        self.user.set_password("newpassword123")
        self.user.save()

        res = self.client.get(f"/api/v1/history/?model=user&object_id={self.user.id_user}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data["data"]["results"]

        # Find update record with changes
        update_record = next((item for item in results if item["action"] == "Actualización"), None)
        self.assertIsNotNone(update_record)
        if update_record and update_record.get("changes"):
            for change in update_record["changes"]:
                if change["field"] == "password":
                    self.assertEqual(change["old"], "********")
                    self.assertEqual(change["new"], "********")
