from django.core.exceptions import ValidationError
from django.db import transaction

from apps.company_info.dto.company_info_dto import (
    CompanyInfoCreateDto,
    CompanyInfoUpdateDto,
)
from apps.company_info.models import CompanyInfo
from apps.core.services.base_service import BaseService


class CompanyInfoService(BaseService[CompanyInfo]):
    """
    Servicio encargado de la lógica de negocio de la
    información de empresa.

    Gestiona la creación y actualización de los datos
    de la empresa de forma centralizada.
    """

    def __init__(self):
        super().__init__(CompanyInfo)

    @staticmethod
    @transaction.atomic
    def create_company_info(
        dto: CompanyInfoCreateDto,
    ) -> CompanyInfo:
        """
        Crea el registro de información de empresa.

        Solo se permite un registro activo a la vez.
        """

        if CompanyInfo.objects.filter(is_active=True).exists():
            raise ValidationError(
                "Ya existe una empresa configurada en el sistema. "
                "Utilice la operación de actualización."
            )

        if CompanyInfo.objects.filter(tax_id=dto.tax_id).exists():
            raise ValidationError(
                "Ya existe un registro con el NIT proporcionado."
            )

        company = CompanyInfo.objects.create(
            business_name=dto.business_name,
            trade_name=dto.trade_name,
            tax_id=dto.tax_id,
            phone=dto.phone,
            mobile=dto.mobile,
            email=dto.email,
            website=dto.website,
            address=dto.address,
            city=dto.city,
            state=dto.state,
            country=dto.country,
            description=dto.description,
            receipt_footer=dto.receipt_footer,
        )

        return company

    @staticmethod
    @transaction.atomic
    def update_company_info(
        company: CompanyInfo,
        dto: CompanyInfoUpdateDto,
    ) -> CompanyInfo:
        """
        Actualiza la información de la empresa.

        Solo se actualizan los campos proporcionados.
        """

        update_fields = ["updated_at"]

        if dto.business_name is not None:
            company.business_name = dto.business_name
            update_fields.append("business_name")

        if dto.trade_name is not None:
            company.trade_name = dto.trade_name
            update_fields.append("trade_name")

        if dto.tax_id is not None:
            if (
                CompanyInfo.objects.filter(tax_id=dto.tax_id)
                .exclude(pk=company.pk)
                .exists()
            ):
                raise ValidationError(
                    "Ya existe un registro con el NIT proporcionado."
                )
            company.tax_id = dto.tax_id
            update_fields.append("tax_id")

        if dto.phone is not None:
            company.phone = dto.phone
            update_fields.append("phone")

        if dto.mobile is not None:
            company.mobile = dto.mobile
            update_fields.append("mobile")

        if dto.email is not None:
            company.email = dto.email
            update_fields.append("email")

        if dto.website is not None:
            company.website = dto.website
            update_fields.append("website")

        if dto.address is not None:
            company.address = dto.address
            update_fields.append("address")

        if dto.city is not None:
            company.city = dto.city
            update_fields.append("city")

        if dto.state is not None:
            company.state = dto.state
            update_fields.append("state")

        if dto.country is not None:
            company.country = dto.country
            update_fields.append("country")

        if dto.description is not None:
            company.description = dto.description
            update_fields.append("description")

        if dto.receipt_footer is not None:
            company.receipt_footer = dto.receipt_footer
            update_fields.append("receipt_footer")

        company.save(update_fields=update_fields)

        return company

    @staticmethod
    @transaction.atomic
    def update_logo(
        company: CompanyInfo,
        logo_file,
    ) -> CompanyInfo:
        """
        Actualiza el logo de la empresa.

        Si ya existe un logo anterior, se reemplaza.
        """

        if company.logo:
            company.logo.delete(save=False)

        company.logo = logo_file
        company.save(update_fields=["logo", "updated_at"])

        return company

    @staticmethod
    @transaction.atomic
    def remove_logo(
        company: CompanyInfo,
    ) -> CompanyInfo:
        """
        Elimina el logo de la empresa.
        """

        if company.logo:
            company.logo.delete(save=False)
            company.logo = None
            company.save(update_fields=["logo", "updated_at"])

        return company

    @staticmethod
    @transaction.atomic
    def deactivate_company_info(
        company: CompanyInfo,
    ) -> None:
        """
        Desactiva lógicamente la información de empresa.
        """

        if not company.is_active:
            raise ValidationError(
                "La información de empresa ya se encuentra desactivada."
            )

        CompanyInfoService().delete(company)

    @staticmethod
    @transaction.atomic
    def restore_company_info(
        company: CompanyInfo,
    ) -> CompanyInfo:
        """
        Restaura la información de empresa desactivada.
        """

        if company.is_active:
            return company

        return CompanyInfoService().restore(company)
