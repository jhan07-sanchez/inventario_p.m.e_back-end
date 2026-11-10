from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.finance.docs.finance_docs import (
    finance_movement_create_schema,
    finance_movement_detail_schema,
    finance_movement_list_schema,
    finance_movement_reverse_schema,
)
from apps.finance.models.financial_movement import FinancialMovement
from apps.finance.selectors.financial_movement_selector import FinancialMovementSelector
from apps.finance.serializers.financial_movement_serializer import (
    FinancialMovementCreateSerializer,
    FinancialMovementListSerializer,
    FinancialMovementReverseSerializer,
)
from apps.finance.services.financial_movement_service import FinancialMovementService
from apps.users.permissions import IsAuthenticatedAndActive


class FinancialMovementViewSet(BaseViewSet):
    """
    ViewSet para listar, registrar y reversar Movimientos Financieros.
    """

    http_method_names = ["get", "post", "head", "options"]
    queryset = FinancialMovement.objects.none()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["description", "reference", "notes", "account__name"]
    ordering_fields = ["movement_date", "amount", "created_at"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("finance.create")),
            "reverse": (IsAuthenticatedAndActive, HasPermission("finance.update")),
        }
        classes = permission_map.get(
            self.action, (IsAuthenticatedAndActive, HasPermission("finance.view"))
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        company_id = getattr(self.request, "company_id", None) or self.request.query_params.get("company_id")
        account_id = self.request.query_params.get("account_id")
        movement_type = self.request.query_params.get("movement_type")
        category_id = self.request.query_params.get("category_id")
        status_param = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        qs = FinancialMovementSelector.get_movements(
            company_id=int(company_id) if company_id else None,
            account_id=int(account_id) if account_id else None,
            movement_type=movement_type,
            category_id=int(category_id) if category_id else None,
            status=status_param,
            start_date=start_date,
            end_date=end_date,
        )
        return self.isolate_queryset(qs)

    def get_serializer_class(self):
        if self.action == "create":
            return FinancialMovementCreateSerializer
        if self.action == "reverse":
            return FinancialMovementReverseSerializer
        return FinancialMovementListSerializer

    @finance_movement_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Movimientos financieros obtenidos.",
            code="FINANCIAL_MOVEMENTS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_movement_detail_schema
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Movimiento financiero obtenido.",
            code="FINANCIAL_MOVEMENT_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_movement_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movement = FinancialMovementService.record_movement(
                serializer.to_dto(),
                user=request.user,
                company_id=getattr(request, "company_id", None),
            )
            output = FinancialMovementListSerializer(movement).data
            return self.success_response(
                message="Movimiento financiero registrado correctamente.",
                code="FINANCIAL_MOVEMENT_RECORDED",
                data=output,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al registrar movimiento financiero."
            )

    @finance_movement_reverse_schema
    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse(self, request, pk=None):
        movement = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            counter = FinancialMovementService.reverse_movement(
                movement_id=movement.pk,
                reason=serializer.validated_data["reason"],
                user=request.user,
            )
            output = FinancialMovementListSerializer(counter).data
            return self.success_response(
                message="Movimiento financiero reversado exitosamente.",
                code="FINANCIAL_MOVEMENT_REVERSED",
                data=output,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al reversar movimiento financiero."
            )
