from django.db.models import QuerySet

from apps.sales.models import Sale, SaleDetail


class SaleSelector:
    """
    Selector encargado de realizar consultas de lectura relacionadas
    con las ventas.

    La clase no modifica información y no contiene lógica de
    persistencia.
    """

    @staticmethod
    def get_all() -> QuerySet[Sale]:
        """
        Obtiene todas las ventas activas.

        Se utilizan relaciones optimizadas para evitar consultas
        innecesarias a la base de datos.
        """

        return (
            Sale.objects.filter(is_active=True)
            .select_related(
                "customer",
                "user",
            )
            .prefetch_related(
                "details__product",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_id(sale_id: int) -> Sale | None:
        """
        Obtiene una venta por su identificador.

        Retorna None si la venta no existe o está inactiva.
        """

        return (
            Sale.objects.filter(
                id_sale=sale_id,
                is_active=True,
            )
            .select_related(
                "customer",
                "user",
            )
            .prefetch_related(
                "details__product",
            )
            .first()
        )

    @staticmethod
    def get_by_sale_number(
        sale_number: str,
    ) -> Sale | None:
        """
        Obtiene una venta mediante su número de venta.
        """

        return (
            Sale.objects.filter(
                sale_number=sale_number,
                is_active=True,
            )
            .select_related(
                "customer",
                "user",
            )
            .prefetch_related(
                "details__product",
            )
            .first()
        )

    @staticmethod
    def get_details(sale_id: int) -> QuerySet[SaleDetail]:
        """
        Obtiene los detalles activos de una venta.

        Incluye la información del producto para evitar consultas
        adicionales al serializar la respuesta.
        """

        return (
            SaleDetail.objects.filter(
                sale_id=sale_id,
                is_active=True,
            )
            .select_related("product")
            .order_by("id_sale_detail")
        )

    @staticmethod
    def exists_by_sale_number(
        sale_number: str,
    ) -> bool:
        """
        Comprueba si existe una venta con el número indicado.
        """

        return Sale.objects.filter(
            sale_number=sale_number,
        ).exists()
