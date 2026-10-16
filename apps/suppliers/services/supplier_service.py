from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    SupplierAlreadyExistsException,
    SupplierInactiveException,
)
from apps.core.services.base_service import BaseService
from apps.suppliers.models import Supplier


class SupplierService(BaseService[Supplier]):
    """
    Servicio encargado de la logica de negocio
    relacionada con los proveedores.
    """

    def __init__(self) -> None:
        super().__init__(Supplier)

    def validate(
        self,
        data: dict,
        instance: Supplier | None = None,
    ) -> dict:
        """
        Valida las reglas de negocio del proveedor.
        """

        document_number = data.get("document_number")

        if document_number:
            document_number = document_number.strip()

            supplier_mgr = getattr(Supplier, "all_objects", Supplier.objects)
            query = supplier_mgr.filter(
                document_number=document_number,
            )

            if instance is not None:
                query = query.exclude(
                    pk=instance.pk,
                )

            if query.exists():
                raise SupplierAlreadyExistsException()

            data["document_number"] = document_number

        return data

    def perform_create(
        self,
        data: dict,
    ) -> Supplier:
        """
        Crea fisicamente el proveedor
        """
        supplier = Supplier(**data)

        supplier.full_clean()
        supplier.save()

        return supplier

    def perform_update(
        self,
        instance: Supplier,
        data: dict,
    ) -> Supplier:
        """
        Actualiza un proveedor existente.
        """
        for field, value in data.items():
            setattr(instance, field, value)

        instance.full_clean()
        instance.save()

        return instance

    def perform_delete(self, instance: Supplier, soft_delete: bool = True) -> None:
        """
        Desactiva un proveedor mediante borrado logico.
        """

        if not instance.is_active:
            raise SupplierInactiveException()

        if soft_delete:
            instance.soft_delete()
        else:
            if hasattr(instance, "hard_delete"):
                instance.hard_delete()
            else:
                instance.delete()

    @staticmethod
    @transaction.atomic
    def create_supplier(
        validated_data: dict,
    ) -> Supplier:
        """
        Crea un nuevo proveedor aplicando
        las reglas de negocio.
        """

        return SupplierService().create(
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def update_supplier(
        supplier: Supplier,
        validared_data: dict,
    ) -> Supplier:
        """
        Actualiza un proveedor aplicando
        las reglas de negocio.
        """

        return SupplierService().update(
            supplier,
            **validared_data,
        )

    @staticmethod
    @transaction.atomic
    def deactivate_supplier(
        supplier: Supplier,
    ) -> Supplier:
        """
        Realiza el borrado logico de un proveedor.

        No elimina fisicamente el registro.
        """

        SupplierService().delete(
            supplier,
            soft_delete=True,
        )

        return supplier

    @staticmethod
    @transaction.atomic
    def restore_supplier(
        supplier: Supplier,
    ) -> Supplier:
        """
        Reactiva un proveedor previamente desactivado.
        """

        return SupplierService().restore(supplier)
