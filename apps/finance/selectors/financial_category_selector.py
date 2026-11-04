from typing import Optional

from django.db.models import QuerySet

from apps.core.selectors.base_selector import BaseSelector
from apps.finance.models.financial_category import FinancialCategory


class FinancialCategorySelector(BaseSelector[FinancialCategory]):
    """
    Selector para consultas de lectura sobre Categorías Financieras.
    """

    def __init__(self):
        super().__init__(FinancialCategory)

    @classmethod
    def get_categories(
        cls,
        category_type: Optional[str] = None,
        company_id: Optional[int] = None,
        include_deleted: bool = False,
    ) -> QuerySet[FinancialCategory]:
        qs = cls().get_all(include_deleted=include_deleted).select_related("company")
        if not include_deleted:
            qs = qs.filter(is_active=True)
        if category_type:
            qs = qs.filter(category_type=category_type)
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    @classmethod
    def get_category_by_id(
        cls,
        category_id: int,
        include_deleted: bool = False,
    ) -> Optional[FinancialCategory]:
        return (
            cls()
            .get_all(include_deleted=include_deleted)
            .select_related("company")
            .filter(pk=category_id)
            .first()
        )

