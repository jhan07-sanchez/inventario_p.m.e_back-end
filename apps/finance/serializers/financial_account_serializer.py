from decimal import Decimal

from rest_framework import serializers

from apps.finance.dto.financial_dto import (
    FinancialAccountCreateDTO,
    FinancialAccountUpdateDTO,
)
from apps.finance.models.financial_account import FinancialAccount


class FinancialAccountListSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(
        source="get_account_type_display", read_only=True
    )

    class Meta:
        model = FinancialAccount
        fields = [
            "id_financial_account",
            "name",
            "account_type",
            "account_type_display",
            "account_number",
            "bank_name",
            "currency",
            "initial_balance",
            "current_balance",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]


class FinancialAccountDetailSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(
        source="get_account_type_display", read_only=True
    )
    company_name = serializers.CharField(
        source="company.business_name", read_only=True, default=None
    )

    class Meta:
        model = FinancialAccount
        fields = [
            "id_financial_account",
            "name",
            "account_type",
            "account_type_display",
            "account_number",
            "bank_name",
            "currency",
            "initial_balance",
            "current_balance",
            "description",
            "company",
            "company_name",
            "is_active",
            "created_at",
            "updated_at",
        ]


class FinancialAccountCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    account_type = serializers.ChoiceField(
        choices=FinancialAccount.AccountType.choices,
        default=FinancialAccount.AccountType.BANK,
    )
    account_number = serializers.CharField(
        max_length=60, required=False, allow_blank=True, default=""
    )
    bank_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    currency = serializers.CharField(max_length=10, default="COP")
    initial_balance = serializers.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    company_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def to_dto(self) -> FinancialAccountCreateDTO:
        data = self.validated_data
        return FinancialAccountCreateDTO(
            name=data["name"],
            account_type=data["account_type"],
            account_number=data.get("account_number", ""),
            bank_name=data.get("bank_name", ""),
            currency=data.get("currency", "COP"),
            initial_balance=data.get("initial_balance", Decimal("0.00")),
            description=data.get("description", ""),
            company_id=data.get("company_id"),
        )


class FinancialAccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    account_type = serializers.ChoiceField(
        choices=FinancialAccount.AccountType.choices, required=False
    )
    account_number = serializers.CharField(
        max_length=60, required=False, allow_blank=True
    )
    bank_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True
    )

    def to_dto(self) -> FinancialAccountUpdateDTO:
        data = self.validated_data
        return FinancialAccountUpdateDTO(
            name=data.get("name"),
            account_type=data.get("account_type"),
            account_number=data.get("account_number"),
            bank_name=data.get("bank_name"),
            description=data.get("description"),
        )

