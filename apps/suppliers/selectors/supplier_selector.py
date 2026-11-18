from django.db.models import QuerySet

from apps.core.selectors.base_selector import BaseSelector
from apps.suppliers.models import Supplier


class SupplierSelector(BaseSelector[Supplier]):
    """
    Selector encargado exclusivamente de realizar consultas
    relacionadas con los proveedores.
    """

    def __init__(self):
        super().__init__(Supplier)

    def get_queryset(
        self,
        include_deleted: bool = False,
        company_id: int | None = None,
    ) -> QuerySet[Supplier]:
        """
        Retorna el queryset base de proveedores ordenados por ID.
        """
        return (
            super()
            .get_queryset(include_deleted=include_deleted, company_id=company_id)
            .order_by("id_supplier")
        )

    @staticmethod
    def get_suppliers(company_id: int | None = None) -> QuerySet[Supplier]:
        """
        Retorna el queryset base de proveedores.

        El filtrado, busqueda y paginacion adicional pueden ser
        aplicados posteriormente por Django REST Framework.
        """
        return SupplierSelector().get_all(company_id=company_id)

    @staticmethod
    def get_supplier_by_id(
        supplier_id: int,
        include_deleted: bool = False,
        company_id: int | None = None,
    ) -> Supplier:
        """
        Obtiene un proveedor mediante su identificador.

        Args:
        supplier_id:
            identificador primario del proveedor.

        Returns:
            Instancia de Supplier.

        Raises:
            Supplier.DoesNotExist:
                Si el proveedor no existe.
        """
        qs = SupplierSelector().get_queryset(
            include_deleted=include_deleted,
            company_id=company_id,
        )
        return qs.get(
            pk=supplier_id,
        )
