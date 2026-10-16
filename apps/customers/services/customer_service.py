from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    CustomerAlreadyExistsException,
    CustomerInactiveException,
)
from apps.core.services.base_service import BaseService
from apps.customers.models import Customer


class CustomerService(BaseService[Customer]):
    """
    Servicio encargado de la lógica de negocio
    relacionada con los clientes.
    """

    def __init__(self) -> None:
        super().__init__(Customer)

    def validate(
        self,
        data: dict,
        instance: Customer | None = None,
    ) -> dict:
        """
        Valida las reglas de negocio del cliente.
        """

        document_number = data.get("document_number")

        if document_number:
            document_number = document_number.strip()

            customer_mgr = getattr(Customer, "all_objects", Customer.objects)
            query = customer_mgr.filter(
                document_number=document_number,
            )

            if instance is not None:
                query = query.exclude(
                    pk=instance.pk,
                )

            if query.exists():
                raise CustomerAlreadyExistsException()

            data["document_number"] = document_number

        return data

    def perform_create(
        self,
        data: dict,
    ) -> Customer:
        """
        Crea físicamente el cliente.
        """

        customer = Customer(**data)

        customer.full_clean()
        customer.save()

        return customer

    def perform_update(
        self,
        instance: Customer,
        data: dict,
    ) -> Customer:
        """
        Actualiza un cliente existente.
        """

        for field, value in data.items():
            setattr(instance, field, value)

        instance.full_clean()
        instance.save()

        return instance

    def perform_delete(
        self,
        instance: Customer,
        soft_delete: bool = True,
    ) -> None:
        """
        Desactiva un cliente mediante borrado lógico.
        """

        if not instance.is_active:
            raise CustomerInactiveException()

        if soft_delete:
            instance.soft_delete()
        else:
            if hasattr(instance, "hard_delete"):
                instance.hard_delete()
            else:
                instance.delete()

    @staticmethod
    @transaction.atomic
    def create_customer(
        validated_data: dict,
    ) -> Customer:
        """
        Crea un nuevo cliente aplicando las reglas de negocio.
        """

        return CustomerService().create(
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def update_customer(
        customer: Customer,
        validated_data: dict,
    ) -> Customer:
        """
        Actualiza un cliente aplicando las reglas de negocio.
        """

        return CustomerService().update(
            customer,
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def deactivate_customer(
        customer: Customer,
    ) -> Customer:
        """
        Realiza el borrado lógico de un cliente.
        """

        CustomerService().delete(
            customer,
            soft_delete=True,
        )

        return customer

    @staticmethod
    @transaction.atomic
    def restore_customer(
        customer: Customer,
    ) -> Customer:
        """
        Reactiva un cliente previamente desactivado.
        """

        return CustomerService().restore(customer)
