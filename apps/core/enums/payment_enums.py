from django.db import models


class PaymentMethod(models.TextChoices):
    """
    Métodos o medios de pago disponibles en el sistema.
    Fuente única de verdad para ventas, pagos, movimientos y compras.
    """
    CASH = "CASH", "Efectivo"
    CARD = "CARD", "Tarjeta"
    TRANSFER = "TRANSFER", "Transferencia"
    CREDIT = "CREDIT", "Crédito"
    OTHER = "OTHER", "Otro"

    @classmethod
    def is_cash(cls, value: str | None) -> bool:
        """Determina si un método de pago corresponde a efectivo físico."""
        return value == cls.CASH


class PaymentStatus(models.TextChoices):
    """
    Estados disponibles para un registro de pago.
    """
    PENDING = "PENDING", "Pendiente"
    COMPLETED = "COMPLETED", "Completado"
    CANCELLED = "CANCELLED", "Cancelado"
    REFUNDED = "REFUNDED", "Reembolsado"
