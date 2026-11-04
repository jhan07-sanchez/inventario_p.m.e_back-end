from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.finance.docs.finance_docs import (
    finance_transfer_cancel_schema,
    finance_transfer_create_schema,
    finance_transfer_detail_schema,
    finance_transfer_list_schema,
)
from apps.finance.models.financial_transfer import FinancialTransfer
from apps.finance.selectors.financial_transfer_selector import FinancialTransferSelector
from apps.finance.serializers.financial_transfer_serializer import (
    FinancialTransferCancelSerializer,
    FinancialTransferCreateSerializer,
    FinancialTransferListSerializer,
)
from apps.finance.services.financial_transfer_service import FinancialTransferService
from apps.users.permissions import IsAuthenticatedAndActive


class FinancialTransferViewSet(BaseViewSet):
    """
    ViewSet para transferencias entre cuentas financieras propias.
    """

    http_method_names = ["get", "post", "head", "options"]
    queryset = FinancialTransfer.objects.none()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "reference",
        "notes",
        "source_account__name",
        "destination_account__name",
    ]
    ordering_fields = ["transfer_date", "amount", "created_at"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("finance.transfer")),
            "cancel": (IsAuthenticatedAndActive, HasPermission("finance.transfer")),
        }
        classes = permission_map.get(
            self.action, (IsAuthenticatedAndActive, HasPermission("finance.view"))
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        source_id = self.request.query_params.get("source_account_id")
        dest_id = self.request.query_params.get("destination_account_id")
        status_param = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        return FinancialTransferSelector.get_transfers(
            source_account_id=int(source_id) if source_id else None,
            destination_account_id=int(dest_id) if dest_id else None,
            status=status_param,
            start_date=start_date,
            end_date=end_date,
        )

    def get_serializer_class(self):
        if self.action == "create":
            return FinancialTransferCreateSerializer
        if self.action == "cancel":
            return FinancialTransferCancelSerializer
        return FinancialTransferListSerializer

    @finance_transfer_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Transferencias financieras obtenidas.",
            code="FINANCIAL_TRANSFERS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_transfer_detail_schema
    def retrieve(self, request, *args, **kwargs):
        instance = FinancialTransferSelector.get_transfer_by_id(kwargs["pk"])
        if not instance:
            return self.error_response(
                message="Transferencia financiera no encontrada.",
                code="FINANCIAL_TRANSFER_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Transferencia financiera obtenida.",
            code="FINANCIAL_TRANSFER_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_transfer_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transfer = FinancialTransferService.execute_transfer(
                serializer.to_dto(), user=request.user
            )
            output = FinancialTransferListSerializer(transfer).data
            return self.success_response(
                message="Transferencia entre cuentas ejecutada exitosamente.",
                code="FINANCIAL_TRANSFER_EXECUTED",
                data=output,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al ejecutar transferencia entre cuentas."
            )

    @finance_transfer_cancel_schema
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transfer = FinancialTransferService.cancel_transfer(
                transfer_id=pk,
                reason=serializer.validated_data["reason"],
                user=request.user,
            )
            output = FinancialTransferListSerializer(transfer).data
            return self.success_response(
                message="Transferencia cancelada y fondos restaurados.",
                code="FINANCIAL_TRANSFER_CANCELLED",
                data=output,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al cancelar transferencia."
            )
