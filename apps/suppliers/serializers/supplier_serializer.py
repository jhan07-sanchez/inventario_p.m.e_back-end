from rest_framework import serializers

from apps.suppliers.models import Supplier
from apps.suppliers.services.supplier_service import SupplierService


class SupplierListSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para listar proveedores.

    Expone únicamente la información necesaria para las tablas
    y listados del sistema.
    """

    class Meta:
        model = Supplier
        fields = (
            "id_supplier",
            "document_type",
            "document_number",
            "first_name",
            "last_name",
            "business_name",
            "email",
            "phone",
            "mobile",
            "address",
            "city",
            "is_active",
        )

        read_only_fields = fields


class SupplierDetailSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para consultar el detalle completo
    de un proveedor.
    """

    class Meta:
        model = Supplier
        fields = (
            "id_supplier",
            "document_type",
            "document_number",
            "first_name",
            "last_name",
            "business_name",
            "email",
            "phone",
            "mobile",
            "address",
            "city",
            "country",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id_supplier",
            "created_at",
            "updated_at",
        )


class SupplierCreateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para crear un proveedor.

    La persistencia es delegada al SupplierService para mantener
    separadas las responsabilidades.
    """

    class Meta:
        model = Supplier
        fields = (
            "document_type",
            "document_number",
            "first_name",
            "last_name",
            "business_name",
            "email",
            "phone",
            "mobile",
            "address",
            "city",
            "country",
            "notes",
            "is_active",
        )

    def create(self, validated_data: dict) -> Supplier:
        """
        Crea un proveedor utilizando el SupplierService.
        """

        return SupplierService.create_supplier(validated_data)


class SupplierUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer utilizado para actualizar un proveedor.

    La persistencia es delegada al SupplierService para mantener
    separadas las responsabilidades.
    """

    class Meta:
        model = Supplier
        fields = (
            "document_type",
            "document_number",
            "first_name",
            "last_name",
            "business_name",
            "email",
            "phone",
            "mobile",
            "address",
            "city",
            "country",
            "notes",
            "is_active",
        )

    def update(
        self,
        instance: Supplier,
        validated_data: dict,
    ) -> Supplier:
        """
        Actualiza un proveedor utilizando el SupplierService.
        """

        return SupplierService.update_supplier(
            supplier=instance,
            validated_data=validated_data,
        )
