from django.db.models import QuerySet

from apps.customers.models import Customer


class CustomerSelector:
    """
    Selector encargado exclusivamente de las consultas relacionadas con clientes.
    """

    @staticmethod
    def get_customers() -> QuerySet[Customer]:
        """
        Obtiene todos los clientes ordenados por ID.
        """

        return Customer.objects.all().order_by("id_customer")

    @staticmethod
    def get_active_customers() -> QuerySet[Customer]:
        """
        Obtiene únicamente los clientes activos.
        """

        return Customer.objects.filter(is_active=True).order_by("id_customer")

    @staticmethod
    def get_customer_by_id(customer_id: int) -> Customer:
        """
        Obtiene un cliente por su identificador único.

        Raises:
            Customer.DoesNotExist: Si el ciente no existe en la base de datos.
        """

        return Customer.objects.get(id_customer=customer_id)

    @staticmethod
    def get_customer_by_document(document_number: str) -> Customer | None:
        """
        Busca un cliente por su numero de documento.
        """
        return Customer.objects.filter(document_number=document_number).first()
