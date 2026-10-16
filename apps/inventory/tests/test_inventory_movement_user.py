from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.inventory.models.inventory_movement import InventoryMovement
from apps.inventory.serializers.inventory_serializer import (
    InventoryMovementDetailSerializer,
    InventoryMovementListSerializer,
)
from apps.inventory.services.inventory_service import InventoryService


class InventoryMovementModelTests(TestCase):
    """
    Pruebas para verificar la presencia del campo user y serializers
    en el modelo InventoryMovement.
    """

    def test_inventory_movement_has_user_field(self):
        """Verifica que el modelo tenga el campo user configurado."""
        fields = [f.name for f in InventoryMovement._meta.get_fields()]
        self.assertIn("user", fields)

    def test_inventory_movement_has_user_index(self):
        """Verifica que el índice inv_mov_user_idx esté definido en Meta."""
        index_names = [idx.name for idx in InventoryMovement._meta.indexes]
        self.assertIn("inv_mov_user_idx", index_names)

    def test_serializers_include_user_and_user_name(self):
        """Verifica que los serializers expongan user y user_name."""
        list_fields = InventoryMovementListSerializer.Meta.fields
        self.assertIn("user", list_fields)
        self.assertIn("user_name", list_fields)

        detail_fields = InventoryMovementDetailSerializer.Meta.fields
        self.assertIn("user", detail_fields)
        self.assertIn("user_name", detail_fields)


class InventoryServiceMovementUserTests(TestCase):
    """
    Pruebas unitarias para validar que el servicio asocie el usuario
    al crear movimientos de inventario.
    """

    @patch("apps.inventory.models.inventory.Inventory.objects")
    @patch("apps.inventory.models.inventory_movement.InventoryMovement.objects.create")
    def test_register_entry_passes_authenticated_user(
        self, mock_create, mock_inv_objects
    ):
        mock_inv = MagicMock()
        mock_inv.pk = 1
        mock_inv.current_stock = Decimal("10.00")

        mock_inv_locked = MagicMock()
        mock_inv_locked.current_stock = Decimal("10.00")
        mock_inv_objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_inv_locked

        mock_user = MagicMock()
        mock_user.is_authenticated = True

        data = {"quantity": Decimal("5.00"), "reference": "REF-001"}
        InventoryService.register_entry(mock_inv, data, user=mock_user)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["user"], mock_user)
        self.assertEqual(
            call_kwargs["movement_type"], InventoryMovement.MovementType.ENTRY
        )

    @patch("apps.inventory.models.inventory.Inventory.objects")
    @patch("apps.inventory.models.inventory_movement.InventoryMovement.objects.create")
    def test_register_exit_passes_authenticated_user(
        self, mock_create, mock_inv_objects
    ):
        mock_inv = MagicMock()
        mock_inv.pk = 1

        mock_inv_locked = MagicMock()
        mock_inv_locked.current_stock = Decimal("20.00")
        mock_inv_objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_inv_locked

        mock_user = MagicMock()
        mock_user.is_authenticated = True

        data = {"quantity": Decimal("5.00"), "reference": "REF-002"}
        InventoryService.register_exit(mock_inv, data, user=mock_user)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["user"], mock_user)
        self.assertEqual(
            call_kwargs["movement_type"], InventoryMovement.MovementType.EXIT
        )

    @patch("apps.inventory.models.inventory.Inventory.objects")
    @patch("apps.inventory.models.inventory_movement.InventoryMovement.objects.create")
    def test_register_adjustment_passes_authenticated_user(
        self, mock_create, mock_inv_objects
    ):
        mock_inv = MagicMock()
        mock_inv.pk = 1

        mock_inv_locked = MagicMock()
        mock_inv_locked.current_stock = Decimal("10.00")
        mock_inv_objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_inv_locked

        mock_user = MagicMock()
        mock_user.is_authenticated = True

        data = {"new_stock": Decimal("15.00"), "reference": "ADJ-001"}
        InventoryService.register_adjustment(mock_inv, data, user=mock_user)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["user"], mock_user)
        self.assertEqual(
            call_kwargs["movement_type"], InventoryMovement.MovementType.ADJUSTMENT
        )
