from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.core.security.services.permission_service import PermissionService
from apps.core.selectors.base_selector import BaseSelector


class SoftDeleteHarmonizationTests(TestCase):
    """
    Pruebas unitarias para validar la sincronización del borrado lógico
    entre BaseModel, ActiveModel y BaseService.
    """

    def test_active_model_soft_delete_synchronizes_state(self):
        """
        Verifica que soft_delete() en ActiveModel actualice tanto is_active como deleted_at.
        """
        from apps.categories.models import Category

        instance = Category(name="Prueba Soft Delete")
        instance.is_active = True
        instance.deleted_at = None
        instance.save = MagicMock()

        instance.soft_delete(save=True)

        self.assertFalse(instance.is_active)
        self.assertIsNotNone(instance.deleted_at)
        instance.save.assert_called_once()
        saved_fields = instance.save.call_args[1].get("update_fields", [])
        self.assertIn("is_active", saved_fields)
        self.assertIn("deleted_at", saved_fields)

    def test_active_model_restore_synchronizes_state(self):
        """
        Verifica que restore() en ActiveModel limpie deleted_at y restaure is_active=True.
        """
        from apps.categories.models import Category

        instance = Category(name="Prueba Restore")
        instance.is_active = False
        instance.deleted_at = timezone.now()
        instance.save = MagicMock()

        instance.restore(save=True)

        self.assertTrue(instance.is_active)
        self.assertIsNone(instance.deleted_at)
        instance.save.assert_called_once()
        saved_fields = instance.save.call_args[1].get("update_fields", [])
        self.assertIn("is_active", saved_fields)
        self.assertIn("deleted_at", saved_fields)
        self.assertIn("is_active", saved_fields)
        self.assertIn("deleted_at", saved_fields)

    def test_base_selector_get_by_id_uses_pk(self):
        """
        Verifica que BaseSelector.get_by_id filtre por pk y no por id literal.
        """
        mock_model = MagicMock()
        selector = BaseSelector(mock_model)

        mock_qs = MagicMock()
        with patch.object(selector, "get_all", return_value=mock_qs):
            selector.get_by_id(42)
            mock_qs.get.assert_called_once_with(pk=42)


class PermissionServiceTests(TestCase):
    """
    Pruebas unitarias para el servicio de permisos optimizado con caché.
    """

    def test_superuser_has_all_permissions(self):
        user = MagicMock()
        user.is_superuser = True

        has_perm = PermissionService.user_has_permission(user, "any.permission")
        self.assertTrue(has_perm)

    @patch.object(PermissionService, "get_effective_permissions")
    def test_user_has_permission_uses_effective_permissions(self, mock_effective):
        mock_effective.return_value = {
            "users.view": True,
            "sales.view": False,
        }
        user = MagicMock()
        user.is_superuser = False

        self.assertTrue(PermissionService.user_has_permission(user, "users.view"))
        self.assertFalse(PermissionService.user_has_permission(user, "sales.view"))
        self.assertFalse(PermissionService.user_has_permission(user, "non_existent"))
        mock_effective.assert_called_with(user)

    @patch("apps.core.security.services.permission_service.cache")
    def test_invalidate_user_cache(self, mock_cache):
        PermissionService.invalidate_user_cache(user_id=10)
        mock_cache.delete.assert_called_once_with("user_permissions_10")

        PermissionService.invalidate_user_cache(user_id=None)
        mock_cache.clear.assert_called_once()
