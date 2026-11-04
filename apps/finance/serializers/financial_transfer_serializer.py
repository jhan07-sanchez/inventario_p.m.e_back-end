from rest_framework import serializers

from apps.finance.dto.financial_dto import FinancialTransferCreateDTO
from apps.finance.models.financial_transfer import FinancialTransfer


class FinancialTransferListSerializer(serializers.ModelSerializer):
    source_account_name = serializers.CharField(
        source="source_account.name", read_only=True
    )
    destination_account_name = serializers.CharField(
        source="destination_account.name", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    user_name = serializers.CharField(
        source="user.username", read_only=True
    )

    class Meta:
        model = FinancialTransfer
        fields = [
            "id_financial_transfer",
            "source_account",
            "source_account_name",
            "destination_account",
            "destination_account_name",
            "amount",
            "transfer_date",
            "reference",
            "notes",
            "status",
            "status_display",
            "user",
            "user_name",
            "created_at",
            "updated_at",
        ]


class FinancialTransferCreateSerializer(serializers.Serializer):
    source_account_id = serializers.IntegerField()
    destination_account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    transfer_date = serializers.DateField()
    reference = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def to_dto(self) -> FinancialTransferCreateDTO:
        data = self.validated_data
        return FinancialTransferCreateDTO(
            source_account_id=data["source_account_id"],
            destination_account_id=data["destination_account_id"],
            amount=data["amount"],
            transfer_date=data["transfer_date"],
            reference=data.get("reference", ""),
            notes=data.get("notes", ""),
        )


class FinancialTransferCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)

