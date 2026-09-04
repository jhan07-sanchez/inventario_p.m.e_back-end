from decimal import Decimal
from typing import Any

from apps.core.exceptions.custom_exceptions import (
    CategoryInactiveException,
    ProductAlreadyExistsException,
    ProductInactiveException,
)
from apps.core.services.base_service import BaseService
from apps.products.models import Product


class ProductService(BaseService[Product]):
    """
    Servicio encargado de la lógica de negocio relacionada
    con los productos.
    """

    def __init__(self):
        super().__init__(Product)

    def validate(
        self,
        data: dict[str, Any],
        instance: Product | None = None,
    ) -> dict[str, Any]:
        """
        Valida las reglas de negocio específicas de un producto.
        """

        code = data.get("code")
        barcode = data.get("barcode")
        category = data.get("category")
        purchase_price = data.get("purchase_price")
        sale_price = data.get("sale_price")
        stock = data.get("stock")
        minimum_stock = data.get("minimum_stock")
        maximum_stock = data.get("maximum_stock")

        queryset = Product.objects.all()

        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)

        if code:
            code = code.strip().upper()
            data["code"] = code

            if queryset.filter(code=code).exists():
                raise ProductAlreadyExistsException()

        if barcode:
            barcode = barcode.strip()

            if queryset.filter(barcode=barcode).exists():
                raise ProductAlreadyExistsException()

            data["barcode"] = barcode

        if category is not None:
            if not category.is_active:
                raise CategoryInactiveException()

        if purchase_price is not None:
            purchase_price = Decimal(str(purchase_price))

            if purchase_price < Decimal("0.00"):
                raise ValueError("El precio de compra no puede ser negativo.")

            data["purchase_price"] = purchase_price

        if sale_price is not None:
            sale_price = Decimal(str(sale_price))

            if sale_price < Decimal("0.00"):
                raise ValueError("El precio de venta no puede ser negativo.")

            data["sale_price"] = sale_price

        if (
            purchase_price is not None
            and sale_price is not None
            and sale_price < purchase_price
        ):
            raise ValueError(
                "El precio de venta no puede ser menor que el precio de compra."
            )

        if stock is not None:
            stock = Decimal(str(stock))

            if stock < Decimal("0.00"):
                raise ValueError("El stock no puede ser negativo.")

            data["stock"] = stock

        if minimum_stock is not None:
            minimum_stock = Decimal(str(minimum_stock))

            if minimum_stock < Decimal("0.00"):
                raise ValueError("El stock mínimo no puede ser negativo.")

            data["minimum_stock"] = minimum_stock

        if maximum_stock is not None:
            maximum_stock = Decimal(str(maximum_stock))

            if maximum_stock < Decimal("0.00"):
                raise ValueError("El stock máximo no puede ser negativo.")

            if minimum_stock is not None and maximum_stock < minimum_stock:
                raise ValueError(
                    "El stock máximo no puede ser menor que el stock mínimo."
                )

            data["maximum_stock"] = maximum_stock

        return data

    def perform_create(self, data: dict[str, Any]) -> Product:
        """
        Crea un producto después de aplicar las reglas de negocio.
        """

        return Product.objects.create(**data)

    def perform_update(
        self,
        instance: Product,
        data: dict[str, Any],
    ) -> Product:
        """
        Actualiza los datos generales del producto.
        """

        for field, value in data.items():
            setattr(instance, field, value)

        instance.full_clean()
        instance.save()

        return instance

    def perform_delete(
        self,
        instance: Product,
        soft_delete: bool = True,
    ) -> None:
        """
        Desactiva o elimina un producto.

        Por defecto se realiza una desactivación lógica.
        """

        if not instance.is_active:
            raise ProductInactiveException()

        if soft_delete:
            instance.is_active = False
            instance.full_clean()
            instance.save(update_fields=["is_active", "updated_at"])
            return

        instance.delete()

    @staticmethod
    def create_product(
        validated_data: dict[str, Any],
    ) -> Product:
        """
        Crea un producto.
        """

        return ProductService().create(**validated_data)

    @staticmethod
    def update_product(
        product: Product,
        validated_data: dict[str, Any],
    ) -> Product:
        """
        Actualiza un producto.
        """

        return ProductService().update(
            product,
            **validated_data,
        )

    @staticmethod
    def deactivate_product(
        product: Product,
    ) -> Product:
        """
        Desactiva un producto.
        """

        ProductService().delete(
            product,
            soft_delete=True,
        )

        return product

    @staticmethod
    def restore_product(
        product: Product,
    ) -> Product:
        """
        Restaura un producto previamente desactivado.
        """

        if product.is_active:
            return product

        return ProductService().restore(product)
