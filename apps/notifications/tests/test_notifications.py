from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.company_info.models import CompanyInfo
from apps.notifications.enums import NotificationCategory, NotificationPriority, NotificationEventType
from apps.notifications.models import Notification
from apps.notifications.selectors import NotificationSelector
from apps.notifications.services import NotificationService
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class NotificationSystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Usuario 1 (Empresa A)
        self.user1 = User.objects.create_user(
            username="user1@company.com",
            email="user1@company.com",
            password="Password123!",
            first_name="User",
            last_name="One",
            document_number="1001",
        )

        # Usuario 2 (Empresa A)
        self.user2 = User.objects.create_user(
            username="user2@company.com",
            email="user2@company.com",
            password="Password123!",
            first_name="User",
            last_name="Two",
            document_number="1002",
        )

        # Usuario 3 (Empresa B - otra empresa)
        self.user3 = User.objects.create_user(
            username="user3@other.com",
            email="user3@other.com",
            password="Password123!",
            first_name="User",
            last_name="Three",
            document_number="1003",
        )

        # Empresa A
        self.company_a = CompanyInfo.objects.create(
            business_name="Empresa A SAS",
            trade_name="Empresa A",
            tax_id="900111222-1",
            owner_user=self.user1,
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )

        # Empresa B
        self.company_b = CompanyInfo.objects.create(
            business_name="Empresa B SAS",
            trade_name="Empresa B",
            tax_id="900333444-2",
            owner_user=self.user3,
            status=CompanyInfo.CompanyStatus.ACTIVE,
        )

        # Roles
        self.role_admin = Role.objects.create(
            role_name="Administrador Empresa",
            company=self.company_a,
            permissions={"inventory.view": True, "sales.view": True, "cash.manage": True},
        )

        # Membresías
        CompanyMembership.objects.create(
            user=self.user1,
            company=self.company_a,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        CompanyMembership.objects.create(
            user=self.user2,
            company=self.company_a,
            role=self.role_admin,
            is_owner=False,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        CompanyMembership.objects.create(
            user=self.user3,
            company=self.company_b,
            role=self.role_admin,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        self.service = NotificationService()
        self.selector = NotificationSelector()

    def test_create_notification_direct_recipient(self):
        """Verifica la creación directa de una notificación para un usuario."""
        notifs = self.service.notify(
            title="Prueba Unitaria",
            message="Contenido de prueba",
            category=NotificationCategory.INVENTORY,
            priority=NotificationPriority.WARNING,
            event_type=NotificationEventType.INVENTORY_STOCK_LOW,
            company_id=self.company_a.id_company,
            recipients=[self.user1],
            action_url="/inventario",
        )
        self.assertEqual(len(notifs), 1)
        notif = notifs[0]
        self.assertEqual(notif.recipient, self.user1)
        self.assertEqual(notif.company_id, self.company_a.id_company)
        self.assertFalse(notif.is_read)
        self.assertIsNone(notif.read_at)

    def test_idempotency_prevents_duplicate_notifications(self):
        """Verifica que no se dupliquen notificaciones con la misma clave de idempotencia."""
        key = "unique_key_123"
        notifs_1 = self.service.notify(
            title="Evento Único",
            message="Primer envío",
            recipients=[self.user1],
            idempotency_key=key,
        )
        self.assertEqual(len(notifs_1), 1)

        # Segundo intento con la misma clave para el mismo usuario
        notifs_2 = self.service.notify(
            title="Evento Único",
            message="Segundo envío duplicado",
            recipients=[self.user1],
            idempotency_key=key,
        )
        self.assertEqual(len(notifs_2), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.user1, idempotency_key=key).count(), 1)

    def test_resolve_recipients_by_company_and_permissions(self):
        """Verifica resolución inteligente de destinatarios por membresía activa y permisos."""
        notifs = self.service.notify(
            title="Alerta de Inventario",
            message="Stock bajo detectado",
            category=NotificationCategory.INVENTORY,
            company_id=self.company_a.id_company,
            permission_code="inventory.view",
        )
        # Tanto user1 (owner) como user2 (con rol que tiene inventory.view) deben recibirla
        recipient_ids = {n.recipient_id for n in notifs}
        self.assertIn(self.user1.pk, recipient_ids)
        self.assertIn(self.user2.pk, recipient_ids)
        # user3 pertenece a otra empresa y no debe recibirla
        self.assertNotIn(self.user3.pk, recipient_ids)

    def test_mark_as_read_and_unread(self):
        """Verifica cambiar estado de lectura individual."""
        notif = self.service.notify(
            title="Mensaje",
            message="Texto",
            recipients=[self.user1],
        )[0]

        # Marcar leída
        updated = self.service.mark_as_read(notif.pk, self.user1)
        self.assertTrue(updated.is_read)
        self.assertIsNotNone(updated.read_at)

        # Marcar no leída
        updated_unread = self.service.mark_as_unread(notif.pk, self.user1)
        self.assertFalse(updated_unread.is_read)
        self.assertIsNone(updated_unread.read_at)

    def test_mark_all_as_read(self):
        """Verifica marcar todas las notificaciones pendientes de un usuario."""
        for i in range(3):
            self.service.notify(
                title=f"Noticia {i}",
                message=f"Contenido {i}",
                recipients=[self.user1],
            )
        unread_before = self.selector.get_user_unread_count(self.user1)
        self.assertEqual(unread_before, 3)

        count = self.service.mark_all_as_read(self.user1)
        self.assertEqual(count, 3)

        unread_after = self.selector.get_user_unread_count(self.user1)
        self.assertEqual(unread_after, 0)

    def test_idor_protection_service(self):
        """Verifica que el usuario 2 no pueda alterar o leer la notificación del usuario 1."""
        notif = self.service.notify(
            title="Privado de User1",
            message="Contenido confidencial",
            recipients=[self.user1],
        )[0]

        # User2 intenta marcarla como leída
        res = self.service.mark_as_read(notif.pk, self.user2)
        self.assertIsNone(res)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

    def test_api_unread_count(self):
        """Verifica el endpoint GET /api/v1/notifications/unread-count/"""
        self.service.notify(
            title="N1",
            message="M1",
            recipients=[self.user1],
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread_count"], 1)

    def test_api_list_and_filters(self):
        """Verifica el endpoint GET /api/v1/notifications/ con filtros de categoría y prioridad."""
        self.service.notify(
            title="Venta registrada",
            message="Venta #1",
            category=NotificationCategory.SALES,
            priority=NotificationPriority.SUCCESS,
            recipients=[self.user1],
        )
        self.service.notify(
            title="Stock agotado",
            message="Producto X",
            category=NotificationCategory.INVENTORY,
            priority=NotificationPriority.CRITICAL,
            recipients=[self.user1],
        )

        self.client.force_authenticate(user=self.user1)

        # Filtro categoría SALES
        res_sales = self.client.get("/api/v1/notifications/?category=SALES")
        self.assertEqual(res_sales.status_code, status.HTTP_200_OK)
        data = res_sales.data.get("data", {})
        results = data.get("results") if isinstance(data, dict) else (data if isinstance(data, list) else res_sales.data.get("results", []))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], NotificationCategory.SALES)

    def test_api_mark_read_and_idor_endpoint(self):
        """Verifica endpoint POST /api/v1/notifications/{id}/read/ e IDOR prevention (404 para ajenas)."""
        notif_user1 = self.service.notify(
            title="De User1",
            message="Mensaje",
            recipients=[self.user1],
        )[0]

        # User2 intenta marcar como leída notificación de User1
        self.client.force_authenticate(user=self.user2)
        res_idor = self.client.post(f"/api/v1/notifications/{notif_user1.pk}/read/")
        self.assertEqual(res_idor.status_code, status.HTTP_404_NOT_FOUND)

        # User1 la marca como leída
        self.client.force_authenticate(user=self.user1)
        res_ok = self.client.post(f"/api/v1/notifications/{notif_user1.pk}/read/")
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        notif_user1.refresh_from_db()
        self.assertTrue(notif_user1.is_read)

    def test_api_mark_all_read(self):
        """Verifica endpoint POST /api/v1/notifications/mark-all-read/"""
        for i in range(2):
            self.service.notify(
                title=f"Aviso {i}",
                message="Aviso",
                recipients=[self.user1],
            )
        self.client.force_authenticate(user=self.user1)
        res = self.client.post("/api/v1/notifications/mark-all-read/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["marked_count"], 2)

    def test_domain_helper_inventory_stock_low(self):
        """Verifica el helper de stock bajo."""
        notifs = self.service.notify_inventory_stock_low(
            product_name="Arroz 1kg",
            current_stock=2.0,
            min_stock=10.0,
            company_id=self.company_a.id_company,
            origin_id="101",
        )
        self.assertGreaterEqual(len(notifs), 1)
        self.assertEqual(notifs[0].category, NotificationCategory.INVENTORY)
        self.assertEqual(notifs[0].priority, NotificationPriority.WARNING)
        self.assertIn("Arroz 1kg", notifs[0].message)
