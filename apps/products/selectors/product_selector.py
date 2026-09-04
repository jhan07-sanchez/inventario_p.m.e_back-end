from django.db import models
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.core.selectors.base_selector import BaseSelector
from apps.products.models import Product


class ProductSelector(BaseSelector[Product]):
    """
    Selector encargado de las consultas relacionadas
    con los productos.

    Los selectors contienen exclusivamente lógica de lectura.
    """

    def __init__(self):
        super().__init__(Product)

    def get_queryset(self) -> QuerySet[Product]:
        """
        Retorna el queryset base de productos optimizando
        las relaciones necesarias.
        """
        return super().get_queryset().select_related("category").order_by("id_product")

    @staticmethod
    def get_products() -> QuerySet[Product]:
        """
        Retorna todos los productos.
        """
        return ProductSelector().get_all()

    @staticmethod
    def get_active_products() -> QuerySet[Product]:
        """
        Retorna únicamente los productos activos.
        """
        return ProductSelector().get_active()

    @staticmethod
    def get_by_id(id_product: int) -> Product:
        """
        Obtiene un producto por su identificador.
        """
        return get_object_or_404(
            ProductSelector().get_queryset(),
            id_product=id_product,
        )

    @staticmethod
    def get_by_code(code: str) -> Product:
        """
        Obtiene un producto mediante su código interno.
        """
        return get_object_or_404(
            ProductSelector().get_queryset(),
            code=code,
        )

    @staticmethod
    def get_by_barcode(barcode: str) -> Product:
        """
        Obtiene un producto mediante su código de barras.
        """
        return get_object_or_404(
            ProductSelector().get_queryset(),
            barcode=barcode,
        )

    @staticmethod
    def product_exists(
        *,
        code: str | None = None,
        barcode: str | None = None,
    ) -> bool:
        """
        Verifica si existe un producto mediante su código
        interno o código de barras.
        """
        selector = ProductSelector()

        if code is not None:
            return selector.exists(code=code)

        if barcode is not None:
            return selector.exists(barcode=barcode)

        return False

    @staticmethod
    def filter_products(
        *,
        name: str | None = None,
        code: str | None = None,
        barcode: str | None = None,
        category: int | None = None,
        is_active: bool | None = None,
        low_stock: bool | None = None,
    ) -> QuerySet[Product]:
        """
        Retorna productos aplicando filtros opcionales.
        """
        queryset = ProductSelector().get_queryset()

        if name:
            queryset = queryset.filter(
                name__icontains=name,
            )

        if code:
            queryset = queryset.filter(
                code__icontains=code,
            )

        if barcode:
            queryset = queryset.filter(
                barcode=barcode,
            )

        if category is not None:
            queryset = queryset.filter(
                category_id=category,
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active,
            )

        if low_stock is True:
            queryset = queryset.filter(
                stock__lte=models.F("minimum_stock"),
            )

        return queryset.order_by("-created_at")
