from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    CustomerInactiveException,
    InvalidSaleStateException,
    InvalidSaleTransitionException,
    ProductInactiveException,
    SaleHasNoDetailsException,
)
from apps.core.services.base_service import BaseService
from apps.customers.models import Customer
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.sales.dto.sale_detail_dto import SaleDetailDto
from apps.sales.dto.sale_dto import SaleCreateDto
from apps.sales.models import Sale
from apps.sales.models import SaleDetail


class SaleService(BaseService[Sale]):
    """
    Servicio encargado de la lógica de negocio de ventas.

    Centraliza la creación de la venta, sus detalles, el cálculo
    de totales y la integración transaccional con el inventario.
    """

    def __init__(self):
        super().__init__(Sale)

    @staticmethod
    @transaction.atomic
    def create_sale(
        dto: SaleCreateDto,
        user,
    ) -> Sale:
        """
        Crea una nueva venta y sus detalles.

        La venta se crea inicialmente en estado PENDING.
        El inventario no se modifica hasta completar la venta.
        """

        try:
            customer = Customer.objects.get(
                pk=dto.customer_id,
            )
        except Customer.DoesNotExist:
            raise ValidationError("El cliente seleccionado no existe.")

        if not customer.is_active:
            raise CustomerInactiveException()

        if not user or not user.is_active:
            raise ValidationError("El usuario que registra la venta no está activo.")

        if not dto.details:
            raise SaleHasNoDetailsException()

        sale = Sale.objects.create(
            sale_number="TEMP",
            customer=customer,
            user=user,
            status=Sale.SaleStatus.PENDING,
            subtotal=Decimal("0.00"),
            discount=dto.discount,
            tax=dto.tax,
            total=Decimal("0.00"),
            payment_method=dto.payment_method,
            notes=dto.notes,
        )

        sale.sale_number = f"VTA-{sale.id_sale:06d}"

        subtotal_sum = Decimal("0.00")

        for detail_dto in dto.details:
            product = SaleService._get_active_product(
                detail_dto,
            )

            unit_price = (
                detail_dto.unit_price
                if detail_dto.unit_price is not None
                else product.sale_price
            )

            if unit_price < Decimal("0.00"):
                raise ValidationError("El precio unitario no puede ser negativo.")

            if detail_dto.quantity <= Decimal("0.00"):
                raise ValidationError("La cantidad del detalle debe ser mayor a cero.")

            if detail_dto.discount < Decimal("0.00"):
                raise ValidationError("El descuento del detalle no puede ser negativo.")

            line_total = detail_dto.quantity * unit_price

            if detail_dto.discount > line_total:
                raise ValidationError(
                    "El descuento del detalle no puede superar el subtotal de la línea."
                )

            line_subtotal = line_total - detail_dto.discount

            SaleDetail.objects.create(
                sale=sale,
                product=product,
                quantity=detail_dto.quantity,
                unit_price=unit_price,
                discount=detail_dto.discount,
                subtotal=line_subtotal,
            )

            subtotal_sum += line_subtotal

        if dto.discount > subtotal_sum:
            raise ValidationError(
                "El descuento global no puede superar el subtotal de la venta."
            )

        total = subtotal_sum - dto.discount + dto.tax

        if total < Decimal("0.00"):
            raise ValidationError("El total de la venta no puede ser negativo.")

        sale.subtotal = subtotal_sum
        sale.total = total

        sale.save(
            update_fields=[
                "sale_number",
                "subtotal",
                "total",
                "updated_at",
            ]
        )

        return sale

    @staticmethod
    def _get_active_product(
        detail_dto: SaleDetailDto,
    ) -> Product:
        """
        Obtiene y valida el producto asociado al detalle.
        """

        try:
            product = Product.objects.get(
                pk=detail_dto.product_id,
            )
        except Product.DoesNotExist:
            raise ValidationError(
                f"El producto con ID {detail_dto.product_id} no existe."
            )

        if not product.is_active:
            raise ProductInactiveException(
                f"El producto {product.name} se encuentra inactivo."
            )

        return product

    @staticmethod
    @transaction.atomic
    def update_sale(
        sale: Sale,
        dto,
    ) -> Sale:
        """
        Actualiza los campos permitidos de una venta.

        Solamente se permiten modificaciones mientras la venta
        permanezca en estado PENDING.
        """

        if sale.status != Sale.SaleStatus.PENDING:
            raise InvalidSaleStateException(
                "Solo se pueden actualizar ventas en estado Pendiente (PENDING)."
            )

        if dto.customer_id is not None:
            try:
                customer = Customer.objects.get(
                    pk=dto.customer_id,
                )
            except Customer.DoesNotExist:
                raise ValidationError("El cliente seleccionado no existe.")

            if not customer.is_active:
                raise CustomerInactiveException()

            sale.customer = customer

        if dto.payment_method is not None:
            sale.payment_method = dto.payment_method

        if dto.notes is not None:
            sale.notes = dto.notes

        sale.save(
            update_fields=[
                "customer",
                "payment_method",
                "notes",
                "updated_at",
            ]
        )

        return sale

    @staticmethod
    @transaction.atomic
    def complete_sale(
        sale: Sale,
        user=None,
    ) -> Sale:
        """
        Completa la venta y descuenta las existencias del inventario.

        Cada detalle genera un movimiento EXIT.
        """

        if sale.status != Sale.SaleStatus.PENDING:
            raise InvalidSaleTransitionException(
                "Solo las ventas Pendientes pueden ser completadas."
            )

        details = sale.details.select_related("product__inventory").filter(
            is_active=True
        )

        if not details.exists():
            raise SaleHasNoDetailsException()

        for detail in details:
            if not hasattr(detail.product, "inventory"):
                raise ValidationError(
                    f"El producto {detail.product.code} "
                    "no tiene un registro de inventario configurado."
                )

            inventory = detail.product.inventory

            exit_data = {
                "quantity": detail.quantity,
                "reference": (f"Venta #{sale.id_sale}"),
                "notes": (f"Salida de inventario por venta #{sale.id_sale}"),
            }

            InventoryService.register_exit(
                inventory=inventory,
                data=exit_data,
                user=user,
            )

        sale.status = Sale.SaleStatus.COMPLETED

        sale.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return sale

    @staticmethod
    @transaction.atomic
    def cancel_sale(
        sale: Sale,
        user=None,
    ) -> Sale:
        """
        Cancela una venta.

        Si la venta ya estaba completada, se revierten las
        salidas de inventario mediante movimientos ENTRY.
        """

        if sale.status == Sale.SaleStatus.CANCELLED:
            raise InvalidSaleTransitionException("La venta ya se encuentra cancelada.")

        if sale.status == Sale.SaleStatus.PENDING:
            sale.status = Sale.SaleStatus.CANCELLED

            sale.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return sale

        if sale.status != Sale.SaleStatus.COMPLETED:
            raise InvalidSaleTransitionException(
                "La venta no puede ser cancelada desde el estado actual."
            )

        details = sale.details.select_related("product__inventory").filter(
            is_active=True
        )

        if not details.exists():
            raise SaleHasNoDetailsException()

        for detail in details:
            if not hasattr(detail.product, "inventory"):
                raise ValidationError(
                    f"El producto {detail.product.code} "
                    "no tiene un registro de inventario configurado."
                )

            inventory = detail.product.inventory

            entry_data = {
                "quantity": detail.quantity,
                "reference": (f"Cancelación venta #{sale.id_sale}"),
                "notes": (
                    "Reversión de salida de inventario "
                    f"por cancelación de venta #{sale.id_sale}"
                ),
            }

            InventoryService.register_entry(
                inventory=inventory,
                data=entry_data,
                user=user,
            )

        sale.status = Sale.SaleStatus.CANCELLED

        sale.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return sale

    @staticmethod
    @transaction.atomic
    def deactivate_sale(
        sale: Sale,
    ) -> None:
        """
        Desactiva lógicamente una venta.
        """

        if not sale.is_active:
            raise ValidationError("La venta ya se encuentra desactivada.")

        SaleService().delete(sale)

    @staticmethod
    @transaction.atomic
    def restore_sale(
        sale: Sale,
    ) -> Sale:
        """
        Restaura lógicamente una venta.
        """

        if sale.is_active:
            raise ValidationError("La venta ya se encuentra activa.")

        return SaleService().restore(sale)
