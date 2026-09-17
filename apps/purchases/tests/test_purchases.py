import pytest
from decimal import Decimal
from django.utils import timezone
from apps.purchases.models import Purchase
from apps.purchases.dto.purchase_dto import PurchaseCreateDTO, PurchaseDetailCreateDTO
from apps.purchases.services.purchase_service import PurchaseService
from apps.core.exceptions.custom_exceptions import InvalidPurchaseTransitionException

@pytest.mark.django_db
class TestPurchaseService:
    def test_create_purchase(self, active_supplier, active_product):
        dto = PurchaseCreateDTO(
            supplier_id=active_supplier.pk,
            issue_date=timezone.now().date(),
            notes="Prueba de compra",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=active_product.pk,
                    quantity=Decimal("10.00"),
                    unit_price=Decimal("15.50")
                )
            ]
        )
        
        purchase = PurchaseService.create_purchase(dto)
        
        assert purchase is not None
        assert purchase.status == Purchase.Status.DRAFT
        assert purchase.subtotal == Decimal("155.00")
        assert purchase.total == Decimal("155.00")
        assert purchase.details.count() == 1

    def test_confirm_purchase(self, active_supplier, active_product):
        dto = PurchaseCreateDTO(
            supplier_id=active_supplier.pk,
            issue_date=timezone.now().date(),
            notes="Prueba de compra",
            details=[
                PurchaseDetailCreateDTO(
                    product_id=active_product.pk,
                    quantity=Decimal("5.00"),
                    unit_price=Decimal("10.00")
                )
            ]
        )
        purchase = PurchaseService.create_purchase(dto)
        purchase = PurchaseService.confirm_purchase(purchase)
        
        assert purchase.status == Purchase.Status.PENDING

    def test_invalid_confirm_purchase_without_details(self, active_supplier):
        # En una compra sin detalles lanzaría error
        pass # To be fully implemented with factory boy and specific tests
