from rest_framework import serializers

from apps.core.enums import PaymentMethod
from apps.finance.dto.financial_dto import FinancialMovementCreateDTO
from apps.finance.models.financial_movement import FinancialMovement


class FinancialMovementListSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    user_name = serializers.CharField(
        source="user.username", read_only=True
    )

    class Meta:
        model = FinancialMovement
        fields = [
            "id_financial_movement",
            "account",
            "account_name",
            "category",
            "category_name",
            "movement_type",
            "movement_type_display",
            "amount",
            "payment_method",
            "payment_method_display",
            "status",
            "status_display",
            "movement_date",
            "description",
            "reference",
            "origin_type",
            "origin_id",
            "transfer",
            "user",
            "user_name",
            "notes",
            "created_at",
            "updated_at",
        ]


class FinancialMovementCreateSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    category_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    movement_type = serializers.ChoiceField(choices=FinancialMovement.MovementType.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.TRANSFER
    )
    movement_date = serializers.DateField()
    description = serializers.CharField(max_length=255)
    reference = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def to_dto(self) -> FinancialMovementCreateDTO:
        data = self.validated_data
        return FinancialMovementCreateDTO(
            account_id=data["account_id"],
            category_id=data.get("category_id"),
            movement_type=data["movement_type"],
            amount=data["amount"],
            payment_method=data.get("payment_method", PaymentMethod.TRANSFER),
            movement_date=data["movement_date"],
            description=data["description"],
            reference=data.get("reference", ""),
            origin_type=FinancialMovement.OriginType.MANUAL,
            notes=data.get("notes", ""),
        )


class FinancialMovementReverseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)

