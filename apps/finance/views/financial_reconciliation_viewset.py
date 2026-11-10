from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.finance.docs.finance_docs import (
    finance_reconciliation_close_schema,
    finance_reconciliation_create_schema,
    finance_reconciliation_detail_schema,
    finance_reconciliation_list_schema,
)
from apps.finance.models.financial_reconciliation import FinancialReconciliation
from apps.finance.selectors.financial_reconciliation_selector import (
    FinancialReconciliationSelector,
)
from apps.finance.serializers.financial_reconciliation_serializer import (
    FinancialReconciliationCreateSerializer,
    FinancialReconciliationListSerializer,
)
from apps.finance.services.financial_reconciliation_service import (
    FinancialReconciliationService,
)
from apps.users.permissions import IsAuthenticatedAndActive


class FinancialReconciliationViewSet(BaseViewSet):
    """
    ViewSet para conciliar y arquear saldos de cuentas financieras.
    """

    http_method_names = ["get", "post", "head", "options"]
    queryset = FinancialReconciliation.objects.none()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["account__name", "notes"]
    ordering_fields = ["end_date", "difference", "created_at"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("finance.reconcile")),
            "close": (IsAuthenticatedAndActive, HasPermission("finance.reconcile")),
        }
        classes = permission_map.get(
            self.action, (IsAuthenticatedAndActive, HasPermission("finance.view"))
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        company_id = getattr(self.request, "company_id", None) or self.request.query_params.get("company_id")
        account_id = self.request.query_params.get("account_id")
        status_param = self.request.query_params.get("status")

        qs = FinancialReconciliationSelector.get_reconciliations(
            company_id=int(company_id) if company_id else None,
            account_id=int(account_id) if account_id else None,
            status=status_param,
        )
        return self.isolate_queryset(qs)

    def get_serializer_class(self):
        if self.action == "create":
            return FinancialReconciliationCreateSerializer
        return FinancialReconciliationListSerializer

    @finance_reconciliation_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Conciliaciones obtenidas.",
            code="FINANCIAL_RECONCILIATIONS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_reconciliation_detail_schema
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Conciliación financiera obtenida.",
            code="FINANCIAL_RECONCILIATION_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_reconciliation_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            recon = FinancialReconciliationService.create_reconciliation(
                serializer.to_dto(),
                user=request.user,
                company_id=getattr(request, "company_id", None),
            )
            output = FinancialReconciliationListSerializer(recon).data
            return self.success_response(
                message="Proceso de conciliación iniciado.",
                code="FINANCIAL_RECONCILIATION_CREATED",
                data=output,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al iniciar conciliación financiera."
            )

    @finance_reconciliation_close_schema
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        recon = self.get_object()
        try:
            closed_recon = FinancialReconciliationService.close_reconciliation(
                reconciliation_id=recon.pk, user=request.user
            )
            output = FinancialReconciliationListSerializer(closed_recon).data
            return self.success_response(
                message="Conciliación aprobada y cerrada satisfactoriamente.",
                code="FINANCIAL_RECONCILIATION_CLOSED",
                data=output,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al cerrar la conciliación."
            )
