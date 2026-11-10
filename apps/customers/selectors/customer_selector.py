from django.db.models import QuerySet

from apps.core.selectors.base_selector import BaseSelector
from apps.customers.models import Customer


class CustomerSelector(BaseSelector[Customer]):
    """
    Selector encargado exclusivamente de las consultas relacionadas con clientes.
    """

    def __init__(self):
        super().__init__(Customer)

    def get_queryset(
        self, include_deleted: bool = False, company_id: int | None = None
    ) -> QuerySet[Customer]:
        """
        Retorna el queryset base de clientes ordenados por ID.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted, company_id=company_id)
            .order_by("id_customer")
        )

    @staticmethod
    def get_customers(company_id: int | None = None) -> QuerySet[Customer]:
        """
        Obtiene todos los clientes ordenados por ID confinado al tenant.
        """
        return CustomerSelector().get_all(company_id=company_id)

    @staticmethod
    def get_active_customers(company_id: int | None = None) -> QuerySet[Customer]:
        """
        Obtiene únicamente los clientes activos de la empresa.
        """
        return CustomerSelector().get_active(company_id=company_id)

    @staticmethod
    def get_customer_by_id(
        customer_id: int, include_deleted: bool = False, company_id: int | None = None
    ) -> Customer:
        """
        Obtiene un cliente por su identificador único asegurando aislamiento tenant.

        Raises:
            Customer.DoesNotExist: Si el cliente no existe en la base de datos o en la empresa.
        """
        manager = Customer.all_objects if include_deleted else Customer.objects
        qs = manager.filter(id_customer=customer_id)
        if company_id is not None:
            qs = qs.filter(company_id=company_id)
        return qs.get()

    @staticmethod
    def get_customer_by_document(
        document_number: str, company_id: int | None = None
    ) -> Customer | None:
        """
        Busca un cliente por su numero de documento en la empresa correspondiente.
        """
        return CustomerSelector().filter(
            document_number=document_number, company_id=company_id
        ).first()
