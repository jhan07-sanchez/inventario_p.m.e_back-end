from rest_framework import serializers

from apps.cash.dto.cash_session_dto import CashSessionCloseDto, CashSessionOpenDto
from apps.cash.models.cash_session import CashSession


class CashSessionRetrieveSerializer(serializers.ModelSerializer):
    cash_register_name = serializers.CharField(
        source="cash_register.name", read_only=True
    )
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    denominations = serializers.SerializerMethodField()

    class Meta:
        model = CashSession
        fields = [
            "id_cash_session",
            "cash_register",
            "cash_register_name",
            "user",
            "user_name",
            "start_time",
            "end_time",
            "opening_balance",
            "expected_balance",
            "counted_balance",
            "difference",
            "status",
            "notes",
            "denominations",
        ]

    def get_denominations(self, obj):
        if not obj.notes or "DENOMINATIONS:" not in obj.notes:
            return None
        try:
            import json
            part = obj.notes.split("DENOMINATIONS:", 1)[1].strip()
            return json.loads(part)
        except Exception:
            return None


class CashSessionOpenSerializer(serializers.Serializer):
    cash_register_id = serializers.IntegerField()
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(allow_blank=True, required=False, default="")

    def to_dto(self) -> CashSessionOpenDto:
        return CashSessionOpenDto(**self.validated_data)


class CashSessionCloseSerializer(serializers.Serializer):
    counted_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(allow_blank=True, required=False, default="")
    denominations = serializers.DictField(required=False, default=dict)

    def to_dto(self) -> CashSessionCloseDto:
        return CashSessionCloseDto(**self.validated_data)
