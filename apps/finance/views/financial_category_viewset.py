from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.finance.docs.finance_docs import (
    finance_category_create_schema,
    finance_category_detail_schema,
    finance_category_list_schema,
)
from apps.finance.models.financial_category import FinancialCategory
from apps.finance.selectors.financial_category_selector import FinancialCategorySelector
from apps.finance.serializers.financial_category_serializer import (
    FinancialCategoryCreateUpdateSerializer,
    FinancialCategorySerializer,
)
from apps.finance.services.financial_category_service import FinancialCategoryService
from apps.users.permissions import IsAuthenticatedAndActive


class FinancialCategoryViewSet(BaseViewSet):
    """
    ViewSet para categorías financieras de ingresos y egresos.
    """

    http_method_names = ["get", "post", "head", "options"]
    queryset = FinancialCategory.objects.none()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "category_type", "created_at"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("finance.create")),
        }
        classes = permission_map.get(
            self.action, (IsAuthenticatedAndActive, HasPermission("finance.view"))
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        cat_type = self.request.query_params.get("category_type")
        company_id = getattr(self.request, "company_id", None) or self.request.query_params.get("company_id")
        qs = FinancialCategorySelector.get_categories(
            category_type=cat_type,
            company_id=int(company_id) if company_id else None,
        )
        return self.isolate_queryset(qs)

    def get_serializer_class(self):
        if self.action == "create":
            return FinancialCategoryCreateUpdateSerializer
        return FinancialCategorySerializer

    @finance_category_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Categorías financieras obtenidas.",
            code="FINANCIAL_CATEGORIES_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_category_detail_schema
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Categoría financiera obtenida.",
            code="FINANCIAL_CATEGORY_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_category_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company_id = getattr(request, "company_id", None) or serializer.validated_data.get("company_id")
        try:
            cat = FinancialCategoryService.create_category(
                name=serializer.validated_data["name"],
                category_type=serializer.validated_data["category_type"],
                description=serializer.validated_data.get("description", ""),
                company_id=company_id,
            )
            output = FinancialCategorySerializer(cat).data
            return self.success_response(
                message="Categoría financiera creada.",
                code="FINANCIAL_CATEGORY_CREATED",
                data=output,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al crear categoría financiera."
            )
