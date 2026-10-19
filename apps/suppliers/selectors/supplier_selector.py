from django.db.models import QuerySet

from apps.suppliers.models import Supplier


class SupplierSelector:
    """
    Selector encargado exclusivamente de realizar consultas
    relacionadas con los proveedores.
    """

    @staticmethod
    def get_suppliers() -> QuerySet[Supplier]:
        """
        Retorna el queryset base de proveedores.

        El filtrado, busqueda y paginacion adicional pueden ser
        aplicados posteriormente por Djando REST Framework.
        """
        return Supplier.objects.all()

    @staticmethod
    def get_supplier_by_id(
        supplier_id: int,
        include_deleted: bool = False,
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
        manager = Supplier.all_objects if include_deleted else Supplier.objects
        return manager.get(
            pk=supplier_id,
        )
