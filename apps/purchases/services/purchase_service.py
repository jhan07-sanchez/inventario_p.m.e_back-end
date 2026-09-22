from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.exceptions.custom_exceptions import (
    SupplierInactiveException,
    ProductInactiveException,
    InvalidPurchaseStateException,
    InvalidPurchaseTransitionException,
    PurchaseHasNoDetailsException,
)
from apps.core.services.base_service import BaseService
from apps.products.models import Product
from apps.purchases.dto.purchase_dto import PurchaseCreateDTO, PurchaseUpdateDTO
from apps.purchases.models import Purchase, PurchaseDetail
from apps.suppliers.models import Supplier
from apps.inventory.services.inventory_service import InventoryService


class PurchaseService(BaseService[Purchase]):
    """
    Servicio encargado de la lógica de negocio de compras.
    Centraliza la creación de la cabecera y el detalle en una misma transacción.
    """

    def __init__(self):
        super().__init__(Purchase)

    @staticmethod
    @transaction.atomic
    def create_purchase(dto: PurchaseCreateDTO) -> Purchase:
        """
        Crea una nueva compra y sus detalles a partir del DTO.
        """

        try:
            supplier = Supplier.objects.get(pk=dto.supplier_id)
        except Supplier.DoesNotExist:
            raise ValidationError("El proveedor seleccionado no existe.")

        if not supplier.is_active:
            raise SupplierInactiveException()

        # Crear la cabecera
        purchase = Purchase.objects.create(
            supplier=supplier,
            issue_date=dto.issue_date or timezone.now().date(),
            notes=dto.notes,
            status=Purchase.Status.DRAFT,
            subtotal=Decimal("0.00"),
            total=Decimal("0.00")
        )

        subtotal_sum = Decimal("0.00")
        total_sum = Decimal("0.00")

        # Crear los detalles
        for detail_dto in dto.details:
            try:
                product = Product.objects.get(pk=detail_dto.product_id)
            except Product.DoesNotExist:
                raise ValidationError(f"El producto con ID {detail_dto.product_id} no existe.")

            if not product.is_active:
                raise ProductInactiveException(f"El producto {product.name} se encuentra inactivo.")

            if detail_dto.quantity <= Decimal("0.00"):
                raise ValidationError("La cantidad del detalle debe ser mayor a cero.")

            if detail_dto.unit_price < Decimal("0.00"):
                raise ValidationError("El precio unitario no puede ser negativo.")

            subtotal_line = detail_dto.quantity * detail_dto.unit_price

            PurchaseDetail.objects.create(
                purchase=purchase,
                product=product,
                quantity=detail_dto.quantity,
                unit_price=detail_dto.unit_price,
                subtotal=subtotal_line,
            )

            subtotal_sum += subtotal_line
            total_sum += subtotal_line

        # Actualizar totales
        purchase.subtotal = subtotal_sum
        purchase.total = total_sum
        purchase.save(update_fields=["subtotal", "total", "updated_at"])

        return purchase

    @staticmethod
    @transaction.atomic
    def update_purchase(purchase: Purchase, dto: PurchaseUpdateDTO) -> Purchase:
        """
        Actualiza los campos permitidos de la cabecera de una compra.
        Solo permitido en estado DRAFT.
        """
        if purchase.status != Purchase.Status.DRAFT:
            raise InvalidPurchaseStateException("Solo se pueden actualizar compras en estado Borrador (DRAFT).")

        if dto.issue_date is not None:
            purchase.issue_date = dto.issue_date

        if dto.notes is not None:
            purchase.notes = dto.notes

        purchase.save(update_fields=["issue_date", "notes", "updated_at"])
        return purchase

    @staticmethod
    @transaction.atomic
    def confirm_purchase(purchase: Purchase) -> Purchase:
        """
        Transición de DRAFT a PENDING.
        """
        if purchase.status != Purchase.Status.DRAFT:
            raise InvalidPurchaseTransitionException("Solo las compras en Borrador pueden ser confirmadas.")

        if not purchase.details.exists():
            raise PurchaseHasNoDetailsException()

        purchase.status = Purchase.Status.PENDING
        purchase.save(update_fields=["status", "updated_at"])
        return purchase

    @staticmethod
    @transaction.atomic
    def receive_purchase(purchase: Purchase, user=None) -> Purchase:
        """
        Transición de PENDING a RECEIVED.
        Registra la entrada en el inventario para cada detalle.
        """
        if purchase.status != Purchase.Status.PENDING:
            raise InvalidPurchaseTransitionException("Solo las compras Pendientes pueden ser recibidas.")

        details = purchase.details.select_related("product__inventory").all()
        if not details:
            raise PurchaseHasNoDetailsException()

        for detail in details:
            # Obtener el inventario del producto
            if not hasattr(detail.product, "inventory"):
                raise ValidationError(f"El producto {detail.product.code} no tiene un registro de inventario configurado.")

            inventory = detail.product.inventory

            # Registrar entrada en el inventario
            entry_data = {
                "quantity": detail.quantity,
                "reference": f"Compra #{purchase.id_purchase}",
                "notes": f"Entrada por recepción de orden de compra #{purchase.id_purchase}",
                "supplier_id": purchase.supplier_id,
            }

            InventoryService.register_entry(
                inventory=inventory,
                data=entry_data,
                user=user
            )

        purchase.status = Purchase.Status.RECEIVED
        purchase.save(update_fields=["status", "updated_at"])
        return purchase

    @staticmethod
    @transaction.atomic
    def complete_purchase(purchase: Purchase) -> Purchase:
        """
        Transición de RECEIVED a COMPLETED.
        Además genera y emite automáticamente la factura de compra asociada.
        """
        if purchase.status != Purchase.Status.RECEIVED:
            raise InvalidPurchaseTransitionException("Solo las compras Recibidas pueden ser completadas.")

        purchase.status = Purchase.Status.COMPLETED
        purchase.save(update_fields=["status", "updated_at"])

        # --- Generación de Factura Automática ---
        from apps.invoices.services.invoice_service import InvoiceService
        from apps.invoices.dto.invoice_dto import InvoiceCreateDTO, InvoiceItemCreateDTO
        from apps.invoices.models import InvoiceTemplate, Invoice
        from django.utils import timezone

        # Buscar plantilla por defecto
        template = InvoiceTemplate.objects.filter(
            document_type=InvoiceTemplate.DocumentType.PURCHASE_INVOICE,
            is_active=True
        ).order_by("-is_default").first()

        if not template:
            # Si no existe, crear una al vuelo para que no falle el proceso
            template = InvoiceTemplate.objects.create(
                name="Plantilla Factura Compra (Auto)",
                document_type=InvoiceTemplate.DocumentType.PURCHASE_INVOICE,
                is_default=True
            )

        # Preparar DTO para la factura
        items_dto = [
            InvoiceItemCreateDTO(
                product_id=detail.product_id,
                quantity=detail.quantity,
                unit_price=detail.unit_price,
            )
            for detail in purchase.details.all()
        ]

        invoice_dto = InvoiceCreateDTO(
            document_type=Invoice.DocumentType.PURCHASE_INVOICE,
            template_id=template.id,
            invoice_number=f"FAC-CMP-{purchase.id_purchase:06d}",
            issue_date=timezone.now().date(),
            purchase_id=purchase.pk,
            notes=f"Factura generada automáticamente por compra #{purchase.id_purchase}",
            items=items_dto
        )

        # Crear y emitir la factura
        invoice = InvoiceService.create_invoice(invoice_dto)
        InvoiceService.issue_invoice(invoice)

        return purchase

    @staticmethod
    @transaction.atomic
    def cancel_purchase(purchase: Purchase) -> Purchase:
        """
        Cancela la compra.
        Solo se permite cancelar compras que no hayan sido recibidas.
        """
        if purchase.status not in [Purchase.Status.DRAFT, Purchase.Status.PENDING]:
            raise InvalidPurchaseTransitionException("No se puede cancelar una compra que ya ha sido recibida o completada.")

        purchase.status = Purchase.Status.CANCELLED
        purchase.save(update_fields=["status", "updated_at"])
        return purchase

    @staticmethod
    @transaction.atomic
    def deactivate_purchase(purchase: Purchase) -> None:
        """
        Borrado lógico de la compra.
        """
        if not purchase.is_active:
            raise ValidationError("La compra ya se encuentra desactivada.")

        PurchaseService().delete(purchase)

    @staticmethod
    @transaction.atomic
    def restore_purchase(purchase: Purchase) -> Purchase:
        """
        Restauración lógica de la compra.
        """
        if purchase.is_active:
            return purchase

        return PurchaseService().restore(purchase)
