from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.configuration.dto import (
    SoftwareVersionCreateDto,
    SoftwareVersionUpdateDto,
)
from apps.configuration.models import SoftwareVersion
from apps.configuration.selectors import SoftwareVersionSelector
from apps.configuration.services import SoftwareVersionService
from apps.core.exceptions.custom_exceptions import (
    SoftwareVersionAlreadyExistsException,
    SoftwareVersionAlreadyPublishedException,
    SoftwareVersionCannotWithdrawException,
    SoftwareVersionDowngradeException,
    SoftwareVersionInvalidSemverException,
)
from apps.users.models import Role, User, UserRole


class SoftwareVersionUnitTests(TestCase):
    """
    Pruebas unitarias para Selectors y Services de Versiones de Software.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="admin_test",
            password="Password123!",
            email="admin_test@example.com",
            document_number="10001",
        )

    def tearDown(self):
        cache.clear()

    def test_semver_parsing_and_comparison(self):
        self.assertEqual(SoftwareVersionSelector.parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(SoftwareVersionSelector.parse_semver("0.0.1"), (0, 0, 1))
        self.assertEqual(SoftwareVersionSelector.parse_semver("invalid"), (0, 0, 0))

        self.assertTrue(SoftwareVersionSelector.is_newer_version("1.2.1", "1.2.0"))
        self.assertTrue(SoftwareVersionSelector.is_newer_version("2.0.0", "1.9.9"))
        self.assertTrue(SoftwareVersionSelector.is_newer_version("1.3.0", "1.2.9"))
        self.assertFalse(SoftwareVersionSelector.is_newer_version("1.2.0", "1.2.0"))
        self.assertFalse(SoftwareVersionSelector.is_newer_version("1.1.9", "1.2.0"))

    def test_create_draft_version_success(self):
        dto = SoftwareVersionCreateDto(
            version="1.1.0",
            name="Version Test",
            description="Descripcion de prueba",
            priority="RECOMMENDED",
            changelog_entries=[
                {"category": "FEATURE", "title": "Nueva función de reportes"},
                {"category": "BUGFIX", "title": "Corrección de cálculo"},
            ],
        )
        version = SoftwareVersionService.create_version(dto, user=self.user)
        self.assertEqual(version.version, "1.1.0")
        self.assertEqual(version.status, SoftwareVersion.Status.DRAFT)
        self.assertEqual(version.changelog_entries.count(), 2)

    def test_create_duplicate_version_fails(self):
        dto = SoftwareVersionCreateDto(version="1.1.0")
        SoftwareVersionService.create_version(dto, user=self.user)
        with self.assertRaises(SoftwareVersionAlreadyExistsException):
            SoftwareVersionService.create_version(dto, user=self.user)

    def test_create_invalid_semver_fails(self):
        dto = SoftwareVersionCreateDto(version="v1.1-bad")
        with self.assertRaises(SoftwareVersionInvalidSemverException):
            SoftwareVersionService.create_version(dto, user=self.user)

    def test_update_draft_version(self):
        version = SoftwareVersionService.create_version(
            SoftwareVersionCreateDto(version="1.1.0", name="Original"), user=self.user
        )
        updated = SoftwareVersionService.update_version(
            version, SoftwareVersionUpdateDto(name="Actualizado"), user=self.user
        )
        self.assertEqual(updated.name, "Actualizado")

    def test_update_published_version_fails(self):
        version = SoftwareVersionService.create_version(
            SoftwareVersionCreateDto(version="1.1.0"), user=self.user
        )
        SoftwareVersionService.publish_version(version, user=self.user)
        with self.assertRaises(SoftwareVersionAlreadyPublishedException):
            SoftwareVersionService.update_version(
                version, SoftwareVersionUpdateDto(name="Nuevo"), user=self.user
            )

    def test_publish_version_enforces_progression(self):
        v1 = SoftwareVersionService.create_version(
            SoftwareVersionCreateDto(version="1.1.0"), user=self.user
        )
        SoftwareVersionService.publish_version(v1, user=self.user)

        # Intentar publicar una versión menor (1.0.5) sin force debe fallar
        v_older = SoftwareVersionService.create_version(
            SoftwareVersionCreateDto(version="1.0.5"), user=self.user
        )
        with self.assertRaises(SoftwareVersionDowngradeException):
            SoftwareVersionService.publish_version(v_older, user=self.user)

        # Con force=True debe permitirse
        forced = SoftwareVersionService.publish_version(
            v_older, user=self.user, force=True, force_reason="Corrección histórica"
        )
        self.assertEqual(forced.status, SoftwareVersion.Status.PUBLISHED)

    def test_withdraw_version(self):
        version = SoftwareVersionService.create_version(
            SoftwareVersionCreateDto(version="1.2.0"), user=self.user
        )
        # Intentar retirar versión en borrador debe fallar
        with self.assertRaises(SoftwareVersionCannotWithdrawException):
            SoftwareVersionService.withdraw_version(version, user=self.user, reason="Error")

        SoftwareVersionService.publish_version(version, user=self.user)
        withdrawn = SoftwareVersionService.withdraw_version(
            version, user=self.user, reason="Vulnerabilidad detectada"
        )
        self.assertEqual(withdrawn.status, SoftwareVersion.Status.WITHDRAWN)

    @override_settings(APP_VERSION="1.0.0")
    def test_check_for_updates_selector(self):
        # Con versión instalada = 1.0.0
        # No hay versiones publicadas
        check = SoftwareVersionSelector.check_for_updates()
        self.assertFalse(check["has_update"])

        # Publicar 1.2.0
        v = SoftwareVersionService.create_version(
            SoftwareVersionCreateDto(
                version="1.2.0",
                priority="MANDATORY",
                changelog_entries=[{"category": "SECURITY", "title": "Parche de seguridad"}],
            ),
            user=self.user,
        )
        SoftwareVersionService.publish_version(v, user=self.user)

        check_after = SoftwareVersionSelector.check_for_updates()
        self.assertTrue(check_after["has_update"])
        self.assertTrue(check_after["is_mandatory"])
        self.assertEqual(check_after["latest_version"], "1.2.0")
        self.assertIsNotNone(check_after["latest_release"])


class SoftwareVersionApiTests(TestCase):
    """
    Pruebas de endpoints HTTP, control estricto de permisos y notificaciones
    para Versiones de Software y Campanita de Notificaciones.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Equipo autorizado de P.M.E. (Superusuario / Gestor de Versiones Oficial)
        self.pme_team = User.objects.create_superuser(
            username="pme_staff",
            password="Password123!",
            email="staff@pme.com",
            document_number="10001",
        )
        self.role_pme = Role.objects.create(
            role_name="PME Staff",
            permissions={"system.manage_releases": True, "settings.view": True},
        )
        UserRole.objects.create(user=self.pme_team, role=self.role_pme)

        # Administrador del Cliente (Tiene permisos de settings.view y settings.update para su negocio,
        # pero NO debe tener permisos para gestionar releases del software P.M.E.)
        self.client_admin = User.objects.create_user(
            username="client_admin",
            password="Password123!",
            email="client_admin@empresa.com",
            document_number="20001",
        )
        self.role_client_admin = Role.objects.create(
            role_name="Administrador del Cliente",
            permissions={"settings.view": True, "settings.update": True},
        )
        UserRole.objects.create(user=self.client_admin, role=self.role_client_admin)

        # Usuario estándar (lector de información)
        self.reader = User.objects.create_user(
            username="reader_user",
            password="Password123!",
            email="reader@empresa.com",
            document_number="20002",
        )
        self.role_reader = Role.objects.create(
            role_name="Lector",
            permissions={"settings.view": True, "settings.update": False},
        )
        UserRole.objects.create(user=self.reader, role=self.role_reader)

        # Token PME Team
        res_pme = self.client.post(
            "/api/v1/auth/login/",
            {"email": "staff@pme.com", "password": "Password123!"},
        )
        self.pme_token = res_pme.data["data"]["access_token"]

        # Token Client Admin
        res_admin = self.client.post(
            "/api/v1/auth/login/",
            {"email": "client_admin@empresa.com", "password": "Password123!"},
        )
        self.admin_token = res_admin.data["data"]["access_token"]

        # Token Reader
        res_reader = self.client.post(
            "/api/v1/auth/login/",
            {"email": "reader@empresa.com", "password": "Password123!"},
        )
        self.reader_token = res_reader.data["data"]["access_token"]

    def tearDown(self):
        cache.clear()

    def test_public_system_info_endpoint(self):
        # GET /api/v1/system/ accesible públicamente
        response = self.client.get("/api/v1/system/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("version", response.data)
        self.assertIn("installed_version", response.data)
        self.assertIn("has_update", response.data)
        self.assertIn("environment", response.data)

    def test_public_check_updates_endpoint(self):
        response = self.client.get("/api/v1/system/check-updates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("has_update", response.data)
        self.assertIn("installed_version", response.data)

    def test_client_admin_cannot_mutate_versions(self):
        """
        Regla Crítica: El Administrador del Cliente NO puede crear, editar,
        publicar ni eliminar versiones del software, a pesar de tener settings.update.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

        # Intento de crear versión -> 403 Forbidden
        res_create = self.client.post(
            "/api/v1/versions/",
            {"version": "1.5.0", "name": "Intento de cliente"},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_403_FORBIDDEN)

    def test_pme_authorized_team_can_manage_version_lifecycle(self):
        """
        El equipo autorizado de P.M.E. sí tiene permisos para gestionar
        el ciclo de vida completo de versiones.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.pme_token}")

        # 1. Crear borrador
        payload = {
            "version": "1.3.0",
            "name": "Actualización Oficial",
            "priority": "RECOMMENDED",
            "description": "Nuevas mejoras globales.",
            "changelog_entries": [
                {"category": "FEATURE", "title": "Módulo de versiones"},
                {"category": "IMPROVEMENT", "title": "Optimización de consultas"},
            ],
        }
        res_create = self.client.post("/api/v1/versions/", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        version_id = res_create.data["data"]["id_version"]

        # 2. Consultar detalle
        res_detail = self.client.get(f"/api/v1/versions/{version_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["data"]["version"], "1.3.0")
        self.assertEqual(res_detail.data["data"]["status"], "DRAFT")

        # 3. Actualizar metadatos
        res_update = self.client.patch(
            f"/api/v1/versions/{version_id}/",
            {"name": "Actualización Oficial Modificada"},
            format="json",
        )
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)

        # 4. Publicar versión
        res_pub = self.client.post(
            f"/api/v1/versions/{version_id}/publish/",
            {"force": False},
            format="json",
        )
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pub.data["data"]["status"], "PUBLISHED")

    def test_client_admin_can_read_and_receive_notifications(self):
        """
        El Administrador del Cliente puede consultar versiones, historial
        y gestionar sus notificaciones personales.
        """
        # Publicar una versión oficial desde el equipo PME
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.pme_token}")
        res_create = self.client.post(
            "/api/v1/versions/",
            {
                "version": "1.4.0",
                "name": "Lanzamiento PME",
                "priority": "RECOMMENDED",
                "changelog_entries": [{"category": "FEATURE", "title": "Nueva función"}],
            },
            format="json",
        )
        v_id = res_create.data["data"]["id_version"]
        self.client.post(f"/api/v1/versions/{v_id}/publish/", format="json")

        # Ahora el Administrador del Cliente consulta las versiones
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

        # 1. Consultar listado -> 200 OK
        res_list = self.client.get("/api/v1/versions/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)

        # 2. Consultar notificaciones pendientes -> Debe tener 1 no leída
        res_notif = self.client.get("/api/v1/versions/notifications/")
        self.assertEqual(res_notif.status_code, status.HTTP_200_OK)
        self.assertEqual(res_notif.data["data"]["unread_count"], 1)
        self.assertEqual(len(res_notif.data["data"]["notifications"]), 1)
        self.assertFalse(res_notif.data["data"]["notifications"][0]["is_read"])

        # 3. Marcar la versión como leída
        res_read = self.client.post(f"/api/v1/versions/{v_id}/read/")
        self.assertEqual(res_read.status_code, status.HTTP_200_OK)
        self.assertEqual(res_read.data["data"]["unread_count"], 0)

        # 4. Volver a consultar notificaciones -> Sigue existiendo en el historial pero marcada como leída
        res_notif_2 = self.client.get("/api/v1/versions/notifications/")
        self.assertEqual(res_notif_2.data["data"]["unread_count"], 0)
        self.assertTrue(res_notif_2.data["data"]["notifications"][0]["is_read"])

    def test_mark_all_notifications_as_read(self):
        # Publicar dos versiones
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.pme_token}")
        for v_num in ["1.6.0", "1.7.0"]:
            res = self.client.post(
                "/api/v1/versions/",
                {"version": v_num, "name": f"Ver {v_num}"},
                format="json",
            )
            self.client.post(f"/api/v1/versions/{res.data['data']['id_version']}/publish/")

        # Cliente tiene 2 no leídas
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res_notif = self.client.get("/api/v1/versions/notifications/")
        self.assertEqual(res_notif.data["data"]["unread_count"], 2)

        # Marcar todas como leídas
        res_all = self.client.post("/api/v1/versions/mark-all-read/")
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(res_all.data["data"]["marked_count"], 2)

        # Verificar conteo = 0
        res_after = self.client.get("/api/v1/versions/notifications/")
        self.assertEqual(res_after.data["data"]["unread_count"], 0)
