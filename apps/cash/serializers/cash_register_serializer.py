from rest_framework import serializers

from apps.cash.models.cash_register import CashRegister


class CashRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y consultar Cajas Registradoras.
    """

    class Meta:
        model = CashRegister
        fields = ["id_cash_register", "name", "description", "is_active", "created_at"]
