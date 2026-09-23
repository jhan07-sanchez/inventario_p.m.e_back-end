from django.db.models import QuerySet

from apps.company_info.models import CompanyInfo


class CompanyInfoSelector:
    """
    Selector encargado de realizar consultas de lectura relacionadas
    con la información de la empresa.

    La clase no modifica información y no contiene lógica de
    persistencia.
    """

    @staticmethod
    def get_current() -> CompanyInfo | None:
        """
        Obtiene la información de empresa activa.

        Retorna la primera empresa activa registrada (singleton).
        """

        return (
            CompanyInfo.objects.filter(is_active=True)
            .order_by("id_company")
            .first()
        )

    @staticmethod
    def get_by_id(company_id: int) -> CompanyInfo | None:
        """
        Obtiene la información de empresa por su identificador.
        """

        return CompanyInfo.objects.filter(
            pk=company_id,
            is_active=True,
        ).first()

    @staticmethod
    def get_all() -> QuerySet[CompanyInfo]:
        """
        Obtiene todos los registros de empresa activos.
        """

        return (
            CompanyInfo.objects.filter(is_active=True)
            .order_by("id_company")
        )

    @staticmethod
    def exists() -> bool:
        """
        Verifica si existe al menos una empresa configurada.
        """

        return CompanyInfo.objects.filter(is_active=True).exists()
