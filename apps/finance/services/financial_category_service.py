from django.db import transaction

from apps.core.exceptions.custom_exceptions import (
    FinancialCategoryAlreadyExistsException,
    FinancialCategoryNotFoundException,
)
from apps.core.services.base_service import BaseService
from apps.finance.models.financial_category import FinancialCategory


class FinancialCategoryService(BaseService[FinancialCategory]):
    """
    Servicio de negocio para la gestión de categorías financieras.
    """

    def __init__(self):
        super().__init__(FinancialCategory)

    @classmethod
    @transaction.atomic
    def create_category(
        cls,
        name: str,
        category_type: str,
        description: str = "",
        company_id: int | None = None,
    ) -> FinancialCategory:
        existing = FinancialCategory.objects.filter(
            name__iexact=name.strip(),
            is_active=True,
        )
        if company_id:
            existing = existing.filter(company_id=company_id)
        if existing.exists():
            raise FinancialCategoryAlreadyExistsException(
                f"Ya existe una categoría financiera activa con el nombre '{name}'."
            )

        return FinancialCategory.objects.create(
            name=name.strip(),
            category_type=category_type,
            description=description.strip(),
            company_id=company_id,
        )

    @classmethod
    @transaction.atomic
    def update_category(
        cls,
        category_id: int,
        name: str | None = None,
        category_type: str | None = None,
        description: str | None = None,
    ) -> FinancialCategory:
        try:
            category = FinancialCategory.objects.select_for_update().get(
                pk=category_id, is_active=True
            )
        except FinancialCategory.DoesNotExist:
            raise FinancialCategoryNotFoundException()

        if name and name.strip() != category.name:
            existing = (
                FinancialCategory.objects.filter(
                    name__iexact=name.strip(),
                    is_active=True,
                )
                .exclude(pk=category_id)
            )
            if category.company_id:
                existing = existing.filter(company_id=category.company_id)
            if existing.exists():
                raise FinancialCategoryAlreadyExistsException(
                    f"Ya existe otra categoría activa con el nombre '{name}'."
                )
            category.name = name.strip()

        if category_type:
            category.category_type = category_type
        if description is not None:
            category.description = description.strip()

        category.save()
        return category

    @classmethod
    @transaction.atomic
    def deactivate_category(cls, category_id: int) -> None:
        try:
            category = FinancialCategory.objects.select_for_update().get(
                pk=category_id, is_active=True
            )
        except FinancialCategory.DoesNotExist:
            raise FinancialCategoryNotFoundException()

        category.soft_delete()
