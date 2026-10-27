from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.cash.models.cash_movement import CashMovement
from apps.cash.models.cash_session import CashSession
from apps.cash.models.payment import Payment
from apps.cash.selectors.cash_session_selector import CashSessionSelector
from apps.core.enums import PaymentMethod
from apps.core.exceptions.custom_exceptions import (
    CashSessionClosedException,
    InsufficientCashException,
    PurchaseNotFoundException,
)
from apps.purchases.dto.purchase_dto import PurchasePayDTO
from apps.purchases.models.purchase import Purchase


class PurchasePaymentService:
    """
    Servicio para la integración financiera de compras con el sistema de caja y pagos.
    Permite liquidar compras a proveedores en efectivo (con impacto en arqueo de caja)
    o mediante métodos electrónicos (transferencia, tarjeta, etc.).
    """

    @staticmethod
    @transaction.atomic
    def pay_purchase(
        purchase_id: int,
        dto: PurchasePayDTO,
        user,
    ) -> dict:
        try:
            purchase = Purchase.objects.select_for_update().get(
                pk=purchase_id, is_active=True
            )
        except Purchase.DoesNotExist:
            raise PurchaseNotFoundException()

        if purchase.status in (Purchase.Status.DRAFT, Purchase.Status.CANCELLED):
            raise ValidationError(
                f"No se pueden registrar pagos en compras en estado {purchase.get_status_display()}."
            )

        if dto.amount <= Decimal("0.00"):
            raise ValidationError("El monto del pago debe ser mayor a cero.")

        # Obtener pagos completados existentes para esta compra
        ref_prefix = f"COMPRA #{purchase.id_purchase}"
        existing_payments = Payment.objects.filter(
            reference__startswith=ref_prefix,
            status=Payment.PaymentStatus.COMPLETED,
            is_active=True,
        )
        total_already_paid = (
            existing_payments.aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )

        pending_balance = purchase.total - total_already_paid
        if dto.amount > pending_balance:
            raise ValidationError(
                f"El monto a pagar (${dto.amount}) supera el saldo pendiente de la compra (${pending_balance})."
            )

        is_cash = PaymentMethod.is_cash(dto.payment_method)
        session = None

        if is_cash:
            if dto.cash_session_id:
                try:
                    session = CashSession.objects.select_for_update().get(
                        pk=dto.cash_session_id, is_active=True
                    )
                except CashSession.DoesNotExist:
                    raise ValidationError("La sesión de caja especificada no existe.")
            else:
                session = CashSessionSelector.get_current_session(user)
                if not session:
                    raise CashSessionClosedException(
                        "Para realizar pagos a proveedores en efectivo debe tener una sesión de caja abierta."
                    )
                session = CashSession.objects.select_for_update().get(pk=session.pk)

            if session.status != CashSession.SessionStatus.OPEN:
                raise CashSessionClosedException(
                    "No se pueden registrar salidas en una sesión de caja cerrada."
                )

            if dto.amount > session.expected_balance:
                raise InsufficientCashException(
                    f"El monto a pagar (${dto.amount}) supera el efectivo disponible en caja (${session.expected_balance})."
                )
        else:
            if dto.cash_session_id:
                session = CashSession.objects.filter(
                    pk=dto.cash_session_id, is_active=True
                ).first()
            else:
                session = CashSessionSelector.get_current_session(user)

        # Crear registro en Payment
        full_ref = f"{ref_prefix}"
        if dto.reference:
            full_ref += f" - {dto.reference}"

        supplier_name = (
            purchase.supplier.business_name
            if purchase.supplier
            else f"Proveedor #{purchase.supplier_id}"
        )
        payment_notes = (
            dto.notes
            or f"Pago de compra #{purchase.id_purchase} a {supplier_name}"
        )

        payment = Payment.objects.create(
            sale=None,
            amount=dto.amount,
            payment_method=dto.payment_method,
            status=Payment.PaymentStatus.COMPLETED,
            reference=full_ref[:100],
            notes=payment_notes,
        )

        # Crear movimiento de caja si aplica
        cash_movement = None
        if session:
            cash_movement = CashMovement.objects.create(
                cash_session=session,
                payment=payment,
                amount=dto.amount,
                movement_type=CashMovement.MovementType.OUT,
                is_cash=is_cash,
                reference=f"PAGO COMPRA #{purchase.id_purchase}",
                description=f"Pago a proveedor: {supplier_name}",
            )

            if is_cash:
                session.expected_balance -= dto.amount
                session.save(update_fields=["expected_balance", "updated_at"])

        new_total_paid = total_already_paid + dto.amount
        new_pending_balance = purchase.total - new_total_paid

        return {
            "payment_id": payment.id_payment,
            "purchase_id": purchase.id_purchase,
            "amount_paid": str(payment.amount),
            "payment_method": payment.payment_method,
            "status": payment.status,
            "reference": payment.reference,
            "cash_movement_id": (
                cash_movement.id_cash_movement if cash_movement else None
            ),
            "total_purchase": str(purchase.total),
            "total_paid": str(new_total_paid),
            "pending_balance": str(new_pending_balance),
            "is_fully_paid": new_pending_balance <= Decimal("0.00"),
        }

    @staticmethod
    def get_purchase_payment_summary(purchase_id: int) -> dict:
        try:
            purchase = Purchase.objects.get(pk=purchase_id, is_active=True)
        except Purchase.DoesNotExist:
            raise PurchaseNotFoundException()

        ref_prefix = f"COMPRA #{purchase.id_purchase}"
        payments = Payment.objects.filter(
            reference__startswith=ref_prefix,
            is_active=True,
        ).order_by("-created_at")

        completed_payments = payments.filter(status=Payment.PaymentStatus.COMPLETED)
        total_paid = (
            completed_payments.aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        pending_balance = purchase.total - total_paid

        return {
            "purchase_id": purchase.id_purchase,
            "supplier_name": (
                purchase.supplier.business_name
                if purchase.supplier
                else f"Proveedor #{purchase.supplier_id}"
            ),
            "purchase_status": purchase.status,
            "total_purchase": str(purchase.total),
            "total_paid": str(total_paid),
            "pending_balance": str(
                pending_balance if pending_balance > 0 else Decimal("0.00")
            ),
            "is_fully_paid": total_paid >= purchase.total,
            "payments": [
                {
                    "payment_id": p.id_payment,
                    "amount": str(p.amount),
                    "payment_method": p.payment_method,
                    "payment_method_display": p.get_payment_method_display(),
                    "status": p.status,
                    "reference": p.reference,
                    "notes": p.notes,
                    "created_at": p.created_at,
                }
                for p in payments
            ],
        }
