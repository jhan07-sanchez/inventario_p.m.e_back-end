from rest_framework import serializers


class FinanceDashboardPeriodSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class FinanceDashboardLiquiditySerializer(serializers.Serializer):
    total_available_money = serializers.CharField()
    financial_accounts_balance = serializers.CharField()
    cash_in_drawers = serializers.CharField()
    total_cash = serializers.CharField()
    bank_balances = serializers.CharField()


class FinanceDashboardCashFlowSerializer(serializers.Serializer):
    period_income = serializers.CharField()
    period_expense = serializers.CharField()
    net_cash_flow = serializers.CharField()


class FinanceDashboardObligationsSerializer(serializers.Serializer):
    accounts_receivable = serializers.CharField()
    accounts_payable = serializers.CharField()


class FinanceDashboardAccountSummarySerializer(serializers.Serializer):
    id_financial_account = serializers.IntegerField()
    name = serializers.CharField()
    account_type = serializers.CharField()
    account_type_display = serializers.CharField()
    bank_name = serializers.CharField(allow_blank=True)
    account_number = serializers.CharField(allow_blank=True)
    currency = serializers.CharField()
    current_balance = serializers.CharField()


class FinanceDashboardRecentMovementSerializer(serializers.Serializer):
    id_financial_movement = serializers.IntegerField()
    account_name = serializers.CharField()
    movement_type = serializers.CharField()
    amount = serializers.CharField()
    movement_date = serializers.CharField()
    description = serializers.CharField()
    category_name = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class FinanceDashboardResponseSerializer(serializers.Serializer):
    period = FinanceDashboardPeriodSerializer()
    liquidity = FinanceDashboardLiquiditySerializer()
    cash_flow = FinanceDashboardCashFlowSerializer()
    obligations = FinanceDashboardObligationsSerializer()
    sales_by_payment_method = serializers.DictField(child=serializers.CharField())
    accounts = FinanceDashboardAccountSummarySerializer(many=True)
    recent_movements = FinanceDashboardRecentMovementSerializer(many=True)

