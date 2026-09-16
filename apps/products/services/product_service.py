from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError

from django.db import transaction

from apps.categories.models import Category
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

    Responsabilidades principales:

    - Validar unicidad del código del producto.
    - Validar unicidad del código de barras.
    - Validar que la categoría esté activa.
    - Validar precios.
    - Validar parámetros de inventario.
    - Crear productos.
    - Actualizar productos.
    - Desactivar productos.
    - Restaurar productos.

    La gestión de movimientos de inventario no pertenece a este
    servicio. Esta responsabilidad será manejada posteriormente
    por el servicio de inventario.
    """

    def __init__(self):
        super().__init__(Product)

    def validate(
        self,
        data: dict[str, Any],
        instance: Product | None = None,
    ) -> dict[str, Any]:
        """
        Ejecuta las validaciones de negocio de un producto.

        Args:
            data: Datos que serán creados o actualizados.
            instance: Producto existente cuando se trata de una
                actualización.

        Returns:
            Los datos normalizados y validados.

        Raises:
            ProductAlreadyExistsException:
                Cuando el código o código de barras ya existe.

            CategoryInactiveException:
                Cuando se intenta asociar una categoría inactiva.

            ValidationError:
                Cuando existe una inconsistencia en los valores
                numéricos del producto.
        """

        data = data.copy()

        code = data.get("code")
        barcode = data.get("barcode")
        category = data.get("category")

        purchase_price = data.get("purchase_price")
        sale_price = data.get("sale_price")

        queryset = Product.objects.all()

        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)

        if code is not None:
            code = code.strip().upper()

            if not code:
                raise ValidationError(
                    "El código del producto no puede estar vacío."
                )

            if queryset.filter(code=code).exists():
                raise ProductAlreadyExistsException()

            data["code"] = code

        if barcode is not None:
            barcode = barcode.strip()

            if barcode:
                if queryset.filter(barcode=barcode).exists():
                    raise ProductAlreadyExistsException()

                data["barcode"] = barcode
            else:
                data["barcode"] = None

        if category is not None:
            if not isinstance(category, Category):
                raise ValidationError(
                    "La categoría proporcionada no es válida."
                )

            if not category.is_active:
                raise CategoryInactiveException()

        if purchase_price is not None:
            purchase_price = Decimal(str(purchase_price))

            if purchase_price < Decimal("0.00"):
                raise ValidationError(
                    "El precio de compra no puede ser negativo."
                )

            data["purchase_price"] = purchase_price

        if sale_price is not None:
            sale_price = Decimal(str(sale_price))

            if sale_price < Decimal("0.00"):
                raise ValidationError(
                    "El precio de venta no puede ser negativo."
                )

            data["sale_price"] = sale_price

        effective_purchase_price = (
            purchase_price
            if purchase_price is not None
            else (
                instance.purchase_price
                if instance is not None
                else None
            )
        )

        effective_sale_price = (
            sale_price
            if sale_price is not None
            else (
                instance.sale_price
                if instance is not None
                else None
            )
        )

        if (
            effective_purchase_price is not None
            and effective_sale_price is not None
            and effective_sale_price < effective_purchase_price
        ):
            raise ValidationError(
                "El precio de venta no puede ser menor "
                "que el precio de compra."
            )

        return data

    def perform_create(
        self,
        data: dict[str, Any],
    ) -> Product:
        """
        Persiste un nuevo producto.
        """

        product = Product(**data)
        product.full_clean()
        product.save()

        return product

    def perform_update(
        self,
        instance: Product,
        data: dict[str, Any],
    ) -> Product:
        """
        Actualiza un producto existente.
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
        Desactiva o elimina físicamente un producto.

        Por defecto se utiliza desactivación lógica mediante
        is_active=False.
        """

        if not instance.is_active:
            raise ProductInactiveException()

        if soft_delete:
            instance.is_active = False
            instance.full_clean()
            instance.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )
            return

        instance.delete()

    @staticmethod
    @transaction.atomic
    def create_product(
        validated_data: dict[str, Any],
    ) -> Product:
        """
        Crea un producto aplicando las reglas de negocio.
        """

        product = ProductService().create(**validated_data)

        # Delegar la creación del inventario inicial al InventoryService
        #from apps.inventory.services.inventory_service import InventoryService
        #InventoryService.create_inventory({"product": product})

        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        product: Product,
        validated_data: dict[str, Any],
    ) -> Product:
        """
        Actualiza un producto aplicando las reglas de negocio.
        """

        previous_is_active = product.is_active

        updated_product = ProductService().update(
            product,
            **validated_data,
        )

        if previous_is_active != updated_product.is_active:
            if hasattr(updated_product, "inventory"):
                inventory = updated_product.inventory
                inventory.is_active = updated_product.is_active
                inventory.full_clean()
                inventory.save(update_fields=["is_active", "updated_at"])

        return updated_product

    @staticmethod
    @transaction.atomic
    def deactivate_product(
        product: Product,
    ) -> Product:
        """
        Desactiva lógicamente un producto y su inventario asociado.
        """

        ProductService().delete(
            product,
            soft_delete=True,
        )

        if hasattr(product, "inventory"):
            inventory = product.inventory
            inventory.is_active = False
            inventory.full_clean()
            inventory.save(update_fields=["is_active", "updated_at"])

        return product

    @staticmethod
    @transaction.atomic
    def restore_product(
        product: Product,
    ) -> Product:
        """
        Restaura un producto previamente desactivado y su inventario.
        """

        product = ProductService().restore(product)

        if hasattr(product, "inventory"):
            inventory = product.inventory
            inventory.is_active = True
            inventory.full_clean()
            inventory.save(update_fields=["is_active", "updated_at"])

        return product
