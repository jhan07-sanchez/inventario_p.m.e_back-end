from rest_framework import serializers
from apps.cash.models.cash_session import CashSession
from apps.cash.dto.cash_session_dto import CashSessionOpenDto, CashSessionCloseDto

class CashSessionRetrieveSerializer(serializers.ModelSerializer):
    cash_register_name = serializers.CharField(source="cash_register.name", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = CashSession
        fields = [
            "id_cash_session", "cash_register", "cash_register_name", "user", "user_name",
            "start_time", "end_time", "opening_balance", "expected_balance",
            "counted_balance", "difference", "status", "notes"
        ]

class CashSessionOpenSerializer(serializers.Serializer):
    cash_register_id = serializers.IntegerField()
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(allow_blank=True, required=False, default="")

    def to_dto(self) -> CashSessionOpenDto:
        return CashSessionOpenDto(**self.validated_data)

class CashSessionCloseSerializer(serializers.Serializer):
    counted_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(allow_blank=True, required=False, default="")

    def to_dto(self) -> CashSessionCloseDto:
        return CashSessionCloseDto(**self.validated_data)
