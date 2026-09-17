from django.db import models
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.purchases.models import PurchaseDetail


class PurchaseDetailSelector(BaseSelector[PurchaseDetail]):
    """
    Selector encargado de las consultas relacionadas
    con los detalles de compra (PurchaseDetail).

    Los selectors contienen exclusivamente lógica de lectura.
    """

    def __init__(self):
        super().__init__(PurchaseDetail)

    def get_queryset(self) -> QuerySet[PurchaseDetail]:
        """
        Retorna el queryset base de detalles de compra optimizando
        las relaciones necesarias (compra y producto).
        """
        return (
            super().get_queryset().select_related("purchase", "product").order_by("id")
        )

    @staticmethod
    def get_purchase_details() -> QuerySet[PurchaseDetail]:
        """
        Retorna todos los detalles de compra.
        """
        return PurchaseDetailSelector().get_all()

    @staticmethod
    def get_active_purchase_details() -> QuerySet[PurchaseDetail]:
        """
        Retorna únicamente los detalles de compra activos.
        """
        return PurchaseDetailSelector().get_active()

    @staticmethod
    def get_by_id(id_detail: int) -> PurchaseDetail:
        """
        Obtiene un detalle de compra por su identificador.
        """
        return get_object_or_404(
            PurchaseDetailSelector().get_queryset(),
            id=id_detail,
        )

    @staticmethod
    def get_by_purchase(purchase_id: int) -> QuerySet[PurchaseDetail]:
        """
        Obtiene todos los detalles pertenecientes a una compra específica.
        """
        return PurchaseDetailSelector().get_queryset().filter(purchase_id=purchase_id)

    @staticmethod
    def get_by_product(product_id: int) -> QuerySet[PurchaseDetail]:
        """
        Obtiene todos los detalles de compra asociados a un producto específico.
        """
        return PurchaseDetailSelector().get_queryset().filter(product_id=product_id)

    @staticmethod
    def purchase_detail_exists(
        *,
        purchase_id: int | None = None,
        product_id: int | None = None,
    ) -> bool:
        """
        Verifica si existe un detalle de compra bajo ciertos criterios.
        """
        selector = PurchaseDetailSelector()

        if purchase_id is not None and product_id is not None:
            return selector.exists(purchase_id=purchase_id, product_id=product_id)

        return False

    @staticmethod
    def filter_purchase_details(
        *,
        purchase_id: int | None = None,
        product_id: int | None = None,
        is_active: bool | None = None,
    ) -> QuerySet[PurchaseDetail]:
        """
        Retorna detalles de compra aplicando filtros opcionales.
        """
        queryset = PurchaseDetailSelector().get_queryset()

        if purchase_id is not None:
            queryset = queryset.filter(
                purchase_id=purchase_id,
            )

        if product_id is not None:
            queryset = queryset.filter(
                product_id=product_id,
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active,
            )

        return queryset.order_by("-id")
