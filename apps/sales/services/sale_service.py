from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

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
from apps.inventory.models import InventoryMovement
from apps.invoices.models import Invoice
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
        customer_id == None indica Consumidor Final (venta POS sin cliente).
        """

        # --- Cliente (opcional) ---
        customer = None
        if dto.customer_id is not None:
            try:
                customer = Customer.objects.get(pk=dto.customer_id)
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
            sale_type=dto.sale_type,
            amount_received=dto.amount_received,
            change_amount=dto.change_amount,
        )

        sale.sale_number = f"VTA-{sale.id_sale:06d}"

        subtotal_sum = Decimal("0.00")

        for detail_dto in dto.details:
            product = SaleService._get_active_product(detail_dto)

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

        update_fields = ["updated_at"]

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
            update_fields.append("customer")

        if dto.payment_method is not None:
            sale.payment_method = dto.payment_method
            update_fields.append("payment_method")

        if dto.notes is not None:
            sale.notes = dto.notes
            update_fields.append("notes")

        sale.save(update_fields=update_fields)

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

        SaleService._create_sale_invoice(sale, details)

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
    def quick_sale(
        dto: SaleCreateDto,
        user,
    ) -> Sale:
        """
        Crea y completa una venta en una única operación atómica (flujo POS).

        Ejecuta en una sola transacción:
          1. Validación de productos y cantidades.
          2. Validación de stock disponible.
          3. Creación de la venta y sus detalles.
          4. Cálculo de totales.
          5. Descuento del inventario.
          6. Registro del movimiento de inventario.
          7. Completado de la venta.
          8. Generación de ticket POS.
          9. Generación de factura (solo si dto.generate_invoice es True).

        Si cualquier paso falla se hace rollback completo.
        """

        # Forzamos sale_type=POS
        from dataclasses import replace as dc_replace
        dto = dc_replace(dto, sale_type=Sale.SaleType.POS)

        sale = SaleService.create_sale(dto, user)
        details = sale.details.select_related("product__inventory").filter(is_active=True)

        for detail in details:
            if not hasattr(detail.product, "inventory"):
                raise ValidationError(
                    f"El producto {detail.product.code} "
                    "no tiene un registro de inventario configurado."
                )

            inventory = detail.product.inventory

            # Validar stock disponible antes de descontar
            if inventory.current_stock < detail.quantity:
                raise ValidationError(
                    f"Stock insuficiente para '{detail.product.name}'. "
                    f"Disponible: {inventory.current_stock}, "
                    f"Solicitado: {detail.quantity}."
                )

            InventoryService.register_exit(
                inventory=inventory,
                data={
                    "quantity": detail.quantity,
                    "reference": f"Venta POS #{sale.id_sale}",
                    "notes": f"Salida de inventario por venta POS #{sale.id_sale}",
                },
                user=user,
            )

        if dto.generate_invoice:
            SaleService._create_sale_invoice(sale, details)

        sale.status = Sale.SaleStatus.COMPLETED
        sale.save(update_fields=["status", "updated_at"])

        return sale

    @staticmethod
    def _create_sale_invoice(
        sale: Sale,
        details,
        generate_invoice: bool = True,
    ) -> None:
        """
        Crea y emite la factura histórica de una venta completada.

        Si generate_invoice es False, no se genera ninguna factura
        (flujo POS ticket sin factura formal).
        """

        if not generate_invoice:
            return

        from apps.invoices.dto.invoice_dto import (
            InvoiceCreateDTO,
            InvoiceItemCreateDTO,
        )
        from apps.invoices.models import Invoice, InvoiceTemplate
        from apps.invoices.services.invoice_service import InvoiceService

        template = InvoiceTemplate.objects.filter(
            document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
            is_active=True,
        ).order_by("-is_default").first()

        if template is None:
            template = InvoiceTemplate.objects.create(
                name="Plantilla Factura Venta (Auto)",
                document_type=InvoiceTemplate.DocumentType.SALE_INVOICE,
                is_default=True,
            )

        items = [
            InvoiceItemCreateDTO(
                product_id=detail.product_id,
                quantity=detail.quantity,
                unit_price=detail.unit_price,
                discount=detail.discount,
            )
            for detail in details
        ]

        invoice = InvoiceService.create_invoice(
            InvoiceCreateDTO(
                document_type=Invoice.DocumentType.SALE_INVOICE,
                template_id=template.id,
                invoice_number=f"FAC-VTA-{sale.id_sale:06d}",
                issue_date=timezone.now().date(),
                sale_id=sale.id_sale,
                discount=sale.discount,
                tax=sale.tax,
                notes=f"Factura generada automáticamente por venta #{sale.id_sale}",
                items=items,
            )
        )

        InvoiceService.issue_invoice(invoice)

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

        sale = (
            Sale.objects.select_for_update()
            .prefetch_related("details__product__inventory")
            .get(pk=sale.pk)
        )

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

            reversal_reference = f"Cancelación venta #{sale.id_sale}"
            reversal_exists = InventoryMovement.objects.filter(
                inventory=inventory,
                movement_type=InventoryMovement.MovementType.ENTRY,
                reference=reversal_reference,
            ).exists()

            if not reversal_exists:
                entry_data = {
                    "quantity": detail.quantity,
                    "reference": reversal_reference,
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

        sale_invoices = Invoice.objects.select_for_update().filter(
            sale=sale,
            document_type=Invoice.DocumentType.SALE_INVOICE,
        )

        for invoice in sale_invoices:
            from apps.invoices.services.invoice_service import InvoiceService

            InvoiceService.cancel_invoice(invoice)

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
            return sale

        return SaleService().restore(sale)
