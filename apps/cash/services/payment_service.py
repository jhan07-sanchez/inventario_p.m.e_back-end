from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cash.dto.payment_dto import PaymentCreateDto
from apps.cash.models.payment import Payment
from apps.core.services.base_service import BaseService
from apps.sales.models.sale import Sale


class PaymentService(BaseService[Payment]):
    """
    Servicio para manejar la creación de pagos.
    """

    def __init__(self):
        super().__init__(Payment)

    @staticmethod
    @transaction.atomic
    def create_payment(dto: PaymentCreateDto) -> Payment:
        sale = None
        if dto.sale_id is not None:
            try:
                sale = Sale.objects.get(pk=dto.sale_id)
            except Sale.DoesNotExist:
                raise ValidationError("La venta asociada no existe.")

        if dto.amount <= Decimal("0.00"):
            raise ValidationError("El monto del pago debe ser mayor a cero.")

        payment = Payment.objects.create(
            sale=sale,
            amount=dto.amount,
            payment_method=dto.payment_method,
            status=dto.status or Payment.PaymentStatus.COMPLETED,
            reference=dto.reference,
            notes=dto.notes,
        )

        return payment
