from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache as django_cache
from django.test import TestCase

from apps.core.security.services.dashboard_metrics_service import (
    DashboardMetricsService,
    _INVENTORY_CACHE_KEYS,
    _PURCHASES_CACHE_KEYS,
    _SALES_CACHE_KEYS,
)
from apps.inventory.services.inventory_service import InventoryService


class DashboardCacheInvalidationTests(TestCase):
    """
    Pruebas para verificar la invalidación granular del caché del dashboard
    tras operaciones en inventario, ventas y compras.
    """

    def setUp(self):
        django_cache.clear()

    def test_invalidate_inventory_cache_clears_inventory_keys(self):
        """Verifica que invalidate_inventory_cache elimine todas las claves de inventario."""
        for key in _INVENTORY_CACHE_KEYS:
            django_cache.set(key, "cached_val")
            self.assertIsNotNone(django_cache.get(key))

        DashboardMetricsService.invalidate_inventory_cache()

        for key in _INVENTORY_CACHE_KEYS:
            self.assertIsNone(django_cache.get(key))

    def test_invalidate_purchases_cache_clears_purchase_keys(self):
        """Verifica que invalidate_purchases_cache elimine las claves de compras."""
        for key in _PURCHASES_CACHE_KEYS:
            django_cache.set(key, "cached_val")
            self.assertIsNotNone(django_cache.get(key))

        DashboardMetricsService.invalidate_purchases_cache()

        for key in _PURCHASES_CACHE_KEYS:
            self.assertIsNone(django_cache.get(key))

    def test_invalidate_sales_cache_clears_sales_and_inventory_keys(self):
        """
        Verifica que invalidate_sales_cache limpie tanto las claves de ventas
        como las de inventario (ya que las ventas impactan existencias).
        """
        for key in _SALES_CACHE_KEYS + _INVENTORY_CACHE_KEYS:
            django_cache.set(key, "cached_val")

        DashboardMetricsService.invalidate_sales_cache()

        for key in _SALES_CACHE_KEYS:
            self.assertIsNone(django_cache.get(key))
        for key in _INVENTORY_CACHE_KEYS:
            self.assertIsNone(django_cache.get(key))

    @patch("apps.inventory.models.inventory.Inventory.objects")
    @patch("apps.inventory.models.inventory_movement.InventoryMovement.objects.create")
    def test_register_entry_triggers_dashboard_cache_invalidation(
        self, mock_create, mock_inv_objects
    ):
        """Verifica que register_entry invalide el caché de inventario del dashboard."""
        mock_inv = MagicMock()
        mock_inv.pk = 1
        mock_inv.current_stock = Decimal("10.00")

        mock_inv_locked = MagicMock()
        mock_inv_locked.current_stock = Decimal("10.00")
        mock_inv_objects.select_for_update.return_value.select_related.return_value.get.return_value = (
            mock_inv_locked
        )

        # Set cache key
        django_cache.set("dashboard_metric_inventory_stock_distribution", {"dummy": 1})
        self.assertIsNotNone(django_cache.get("dashboard_metric_inventory_stock_distribution"))

        data = {"quantity": Decimal("10.00"), "reference": "REF-ENTRY"}
        InventoryService.register_entry(mock_inv, data)

        self.assertIsNone(django_cache.get("dashboard_metric_inventory_stock_distribution"))
