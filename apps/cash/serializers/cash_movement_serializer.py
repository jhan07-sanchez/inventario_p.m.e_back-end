from rest_framework import serializers

from apps.cash.dto.cash_movement_dto import CashMovementCreateDto
from apps.cash.models.cash_movement import CashMovement


class CashMovementRetrieveSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(
        source="payment.payment_method", read_only=True, allow_null=True, default=None
    )
    payment_reference = serializers.CharField(
        source="payment.reference", read_only=True, allow_null=True, default=None
    )
    payment = serializers.PrimaryKeyRelatedField(read_only=True, allow_null=True)

    class Meta:
        model = CashMovement
        fields = [
            "id_cash_movement",
            "cash_session",
            "payment",
            "amount",
            "movement_type",
            "is_cash",
            "reference",
            "description",
            "payment_method",
            "payment_reference",
            "created_at",
        ]


class CashMovementCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    movement_type = serializers.ChoiceField(choices=CashMovement.MovementType.choices)
    is_cash = serializers.BooleanField(default=True)
    reference = serializers.CharField(allow_blank=True, required=False, default="")
    description = serializers.CharField(allow_blank=True, required=False, default="")

    def to_dto(self, session_id: int) -> CashMovementCreateDto:
        return CashMovementCreateDto(
            cash_session_id=session_id,
            amount=self.validated_data["amount"],
            movement_type=self.validated_data["movement_type"],
            is_cash=self.validated_data["is_cash"],
            reference=self.validated_data.get("reference", ""),
            description=self.validated_data.get("description", ""),
        )
