from rest_framework import serializers

from apps.finance.dto.financial_dto import FinancialReconciliationCreateDTO
from apps.finance.models.financial_reconciliation import FinancialReconciliation


class FinancialReconciliationListSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = FinancialReconciliation
        fields = [
            "id_reconciliation",
            "account",
            "account_name",
            "start_date",
            "end_date",
            "statement_balance",
            "book_balance",
            "difference",
            "status",
            "status_display",
            "reconciled_at",
            "user",
            "user_name",
            "notes",
            "created_at",
            "updated_at",
        ]


class FinancialReconciliationCreateSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    statement_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def to_dto(self) -> FinancialReconciliationCreateDTO:
        data = self.validated_data
        return FinancialReconciliationCreateDTO(
            account_id=data["account_id"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            statement_balance=data["statement_balance"],
            notes=data.get("notes", ""),
        )

