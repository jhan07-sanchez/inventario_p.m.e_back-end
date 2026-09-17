from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.services.base_service import BaseService
from apps.core.exceptions.custom_exceptions import (
    InvoiceTemplateNotFoundException,
    InvalidInvoiceStateException,
    InvalidInvoiceTransitionException,
    InvoiceHasNoItemsException,
    ProductInactiveException,
)
from apps.invoices.dto.invoice_dto import InvoiceCreateDTO, InvoiceUpdateDTO
from apps.invoices.models import Invoice, InvoiceItem, InvoiceTemplate
from apps.products.models import Product
from apps.purchases.models import Purchase


class InvoiceService(BaseService[Invoice]):
    """
    Servicio encargado de la lógica de negocio de facturación.
    """

    def __init__(self):
        super().__init__(Invoice)

    @staticmethod
    @transaction.atomic
    def create_invoice(dto: InvoiceCreateDTO) -> Invoice:
        # Validar plantilla
        try:
            template = InvoiceTemplate.objects.get(pk=dto.template_id)
        except InvoiceTemplate.DoesNotExist:
            raise InvoiceTemplateNotFoundException()

        if not template.is_active:
            raise ValidationError("La plantilla seleccionada se encuentra inactiva.")

        # Validar compra relacionada (si aplica)
        purchase = None
        if dto.purchase_id:
            try:
                purchase = Purchase.objects.get(pk=dto.purchase_id)
            except Purchase.DoesNotExist:
                raise ValidationError("La compra relacionada no existe.")

        # Validar items
        if not dto.items:
            raise InvoiceHasNoItemsException()

        # Chequear unicidad manual por race conditions
        if Invoice.objects.filter(invoice_number=dto.invoice_number).exists():
            raise ValidationError("El número de factura ya existe.")

        # Crear cabecera
        invoice = Invoice.objects.create(
            invoice_number=dto.invoice_number,
            document_type=dto.document_type,
            template=template,
            purchase=purchase,
            issue_date=dto.issue_date or timezone.now().date(),
            due_date=dto.due_date,
            notes=dto.notes,
            status=Invoice.Status.DRAFT,
            subtotal=Decimal("0.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=Decimal("0.00"),
        )

        subtotal_sum = Decimal("0.00")
        discount_sum = Decimal("0.00")
        tax_sum = Decimal("0.00")
        total_sum = Decimal("0.00")

        for item_dto in dto.items:
            try:
                product = Product.objects.get(pk=item_dto.product_id)
            except Product.DoesNotExist:
                raise ValidationError(f"El producto con ID {item_dto.product_id} no existe.")

            if not product.is_active:
                raise ProductInactiveException(f"El producto {product.name} está inactivo.")

            if item_dto.quantity <= Decimal("0.00"):
                raise ValidationError("La cantidad debe ser mayor a cero.")

            if item_dto.unit_price < Decimal("0.00"):
                raise ValidationError("El precio unitario no puede ser negativo.")

            line_subtotal = item_dto.quantity * item_dto.unit_price
            
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=item_dto.quantity,
                unit_price=item_dto.unit_price,
                discount=item_dto.discount,
                tax=item_dto.tax,
                subtotal=line_subtotal,
            )

            subtotal_sum += line_subtotal
            discount_sum += item_dto.discount
            tax_sum += item_dto.tax
            total_sum += (line_subtotal - item_dto.discount + item_dto.tax)

        invoice.subtotal = subtotal_sum
        invoice.discount = discount_sum
        invoice.tax = tax_sum
        invoice.total = total_sum
        invoice.save(update_fields=["subtotal", "discount", "tax", "total", "updated_at"])

        return invoice

    @staticmethod
    @transaction.atomic
    def update_invoice(invoice: Invoice, dto: InvoiceUpdateDTO) -> Invoice:
        if invoice.status != Invoice.Status.DRAFT:
            raise InvalidInvoiceStateException("Solo se pueden actualizar facturas en estado Borrador (DRAFT).")

        if dto.issue_date is not None:
            invoice.issue_date = dto.issue_date
        if dto.due_date is not None:
            invoice.due_date = dto.due_date
        if dto.notes is not None:
            invoice.notes = dto.notes

        invoice.save(update_fields=["issue_date", "due_date", "notes", "updated_at"])
        return invoice

    @staticmethod
    @transaction.atomic
    def issue_invoice(invoice: Invoice) -> Invoice:
        """
        Transita de DRAFT a ISSUED.
        """
        if invoice.status != Invoice.Status.DRAFT:
            raise InvalidInvoiceTransitionException("Solo las facturas en Borrador pueden ser emitidas.")

        if not invoice.items.exists():
            raise InvoiceHasNoItemsException()

        invoice.status = Invoice.Status.ISSUED
        invoice.save(update_fields=["status", "updated_at"])
        return invoice

    @staticmethod
    @transaction.atomic
    def cancel_invoice(invoice: Invoice) -> Invoice:
        """
        Transita a CANCELLED.
        """
        if invoice.status == Invoice.Status.CANCELLED:
            raise InvalidInvoiceTransitionException("La factura ya se encuentra anulada.")

        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        return invoice

    @staticmethod
    @transaction.atomic
    def deactivate_invoice(invoice: Invoice) -> None:
        """
        Borrado lógico de la factura.
        """
        if not invoice.is_active:
            raise ValidationError("La factura ya se encuentra desactivada.")
        
        InvoiceService().delete(invoice)
