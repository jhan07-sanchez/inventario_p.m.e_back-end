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
from apps.sales.models import Sale


class InvoiceService(BaseService[Invoice]):
    """
    Servicio encargado de la lógica de negocio de facturación.
    """

    def __init__(self):
        super().__init__(Invoice)

    @staticmethod
    @transaction.atomic
    def create_invoice(dto: InvoiceCreateDTO) -> Invoice:
        purchase, sale = InvoiceService._resolve_origin(dto)

        # Validar plantilla
        try:
            template = InvoiceTemplate.objects.get(pk=dto.template_id)
        except InvoiceTemplate.DoesNotExist:
            raise InvoiceTemplateNotFoundException()

        if not template.is_active:
            raise ValidationError("La plantilla seleccionada se encuentra inactiva.")

        # Validar items
        if not dto.items:
            raise InvoiceHasNoItemsException()

        # Chequear unicidad manual por race conditions
        if Invoice.objects.filter(invoice_number=dto.invoice_number).exists():
            raise ValidationError("El número de factura ya existe.")

        # Obtener datos de la empresa activos
        from apps.company_info.models import CompanyInfo
        company = CompanyInfo.objects.filter(is_active=True).first()
        
        c_name = company.business_name if company else ""
        c_tax_id = company.tax_id if company else ""
        c_address = company.address if company else ""
        c_phone = company.phone or company.mobile if company else ""
        c_email = company.email if company else ""

        # Crear cabecera
        invoice = Invoice.objects.create(
            invoice_number=dto.invoice_number,
            document_type=dto.document_type,
            template=template,
            purchase=purchase,
            sale=sale,
            issue_date=dto.issue_date or timezone.now().date(),
            due_date=dto.due_date,
            notes=dto.notes,
            status=Invoice.Status.DRAFT,
            subtotal=Decimal("0.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=Decimal("0.00"),
            company_name_snapshot=c_name,
            company_tax_id_snapshot=c_tax_id,
            company_address_snapshot=c_address,
            company_phone_snapshot=c_phone,
            company_email_snapshot=c_email,
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

        if dto.discount < Decimal("0.00") or dto.tax < Decimal("0.00"):
            raise ValidationError(
                "El descuento y los impuestos de la factura no pueden ser negativos."
            )

        if dto.discount > subtotal_sum - discount_sum:
            raise ValidationError(
                "El descuento de la factura no puede superar el subtotal neto."
            )

        discount_sum += dto.discount
        tax_sum += dto.tax
        total_sum += dto.tax - dto.discount

        if total_sum < Decimal("0.00"):
            raise ValidationError("El total de la factura no puede ser negativo.")

        invoice.subtotal = subtotal_sum
        invoice.discount = discount_sum
        invoice.tax = tax_sum
        invoice.total = total_sum
        invoice.save(update_fields=["subtotal", "discount", "tax", "total", "updated_at"])

        return invoice

    @staticmethod
    def _resolve_origin(dto: InvoiceCreateDTO) -> tuple[Purchase | None, Sale | None]:
        """
        Resuelve y valida el único origen empresarial de la factura.
        """

        has_purchase = dto.purchase_id is not None
        has_sale = dto.sale_id is not None

        if has_purchase == has_sale:
            raise ValidationError(
                "La factura debe estar relacionada exactamente con una compra o una venta."
            )

        if has_purchase:
            try:
                purchase = Purchase.objects.get(pk=dto.purchase_id)
            except Purchase.DoesNotExist as exception:
                raise ValidationError(
                    "La compra relacionada no existe."
                ) from exception

            if dto.document_type != Invoice.DocumentType.PURCHASE_INVOICE:
                raise ValidationError(
                    "Las compras solo pueden generar facturas de compra."
                )

            return purchase, None

        try:
            sale = Sale.objects.get(pk=dto.sale_id)
        except Sale.DoesNotExist as exception:
            raise ValidationError(
                "La venta relacionada no existe."
            ) from exception

        if dto.document_type != Invoice.DocumentType.SALE_INVOICE:
            raise ValidationError(
                "Las ventas solo pueden generar facturas de venta."
            )

        return None, sale

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
        Transita una factura emitida a CANCELLED.
        """
        if invoice.status == Invoice.Status.CANCELLED:
            raise InvalidInvoiceTransitionException("La factura ya se encuentra anulada.")

        if invoice.status != Invoice.Status.ISSUED:
            raise InvalidInvoiceTransitionException(
                "Solo las facturas emitidas pueden ser anuladas."
            )

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

    @staticmethod
    @transaction.atomic
    def restore_invoice(invoice: Invoice) -> Invoice:
        """
        Restaura una factura previamente desactivada.
        """

        if invoice.is_active:
            return invoice

        return InvoiceService().restore(invoice)
