from rest_framework import serializers

from apps.customers.models import Customer
from apps.customers.services.customer_service import CustomerService



class CustomerListSerializer(serializers.ModelSerializer):
    """
    Serializer utlizado para listar clientes.

    Expone unicamente  la informacion necesaria para las tablas y listados del sistema.
    """

    class Meta:
        model = Customer
        fields = (
            "id_customer",
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



class CustomerDetailSerializer(serializers.ModelSerializer):
    """
    Serializer utlizado para consultar el detalle completo de un cliente.
    """

    class Meta:
        model = Customer
        fields = (
            "id_customer",
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
            "id_customer",
            "created_at",
            "updated_at",
        )




class CustomerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer utlizado para crear un cliente.

    La persistencia es delegada al CustomerService para
    mantener separadas las responsabilidades.
    """

    class Meta:
        model = Customer
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

    def create(self, validated_data):
        """
        Crea un cliente utilizando el CustomerService.
        """
        return CustomerService.create_customer(validated_data)




class CustomerUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer utlizado para actualizar un cliente.

    La persistencia es delegada al CustomerService para
    mantener separadas las responsabilidades.
    """

    class Meta:
        model = Customer
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


    def update(self, instance, validated_data):
        """
        Actualiza un cliente utilizando el CustomerService.
        """
        return CustomerService.update_customer(customer=instance, validated_data=validated_data)
