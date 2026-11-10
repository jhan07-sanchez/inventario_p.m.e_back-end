from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.exceptions.custom_exceptions import (
    FinancialAccountAlreadyExistsException,
    FinancialAccountNotFoundException,
)
from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.finance.docs.finance_docs import (
    finance_account_create_schema,
    finance_account_delete_schema,
    finance_account_detail_schema,
    finance_account_list_schema,
    finance_account_restore_schema,
    finance_account_update_schema,
)
from apps.finance.models.financial_account import FinancialAccount
from apps.finance.selectors.financial_account_selector import FinancialAccountSelector
from apps.finance.serializers.financial_account_serializer import (
    FinancialAccountCreateSerializer,
    FinancialAccountDetailSerializer,
    FinancialAccountListSerializer,
    FinancialAccountUpdateSerializer,
)
from apps.finance.services.financial_account_service import FinancialAccountService
from apps.users.permissions import IsAuthenticatedAndActive


class FinancialAccountViewSet(BaseViewSet):
    """
    ViewSet para la administración de Cuentas Financieras (cajas, bancos, billeteras).
    """

    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    queryset = FinancialAccount.objects.none()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "bank_name", "account_number", "description"]
    ordering_fields = ["name", "current_balance", "created_at"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("finance.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("finance.create")),
            "update": (IsAuthenticatedAndActive, HasPermission("finance.update")),
            "destroy": (IsAuthenticatedAndActive, HasPermission("finance.delete")),
            "restore": (IsAuthenticatedAndActive, HasPermission("finance.update")),
        }
        classes = permission_map.get(
            self.action, (IsAuthenticatedAndActive, HasPermission("finance.view"))
        )
        return [permission() for permission in classes]

    def get_queryset(self):
        company_id = getattr(self.request, "company_id", None) or self.request.query_params.get("company_id")
        account_type = self.request.query_params.get("account_type")
        include_deleted_param = self.request.query_params.get("include_deleted")
        include_deleted = (
            include_deleted_param.lower() in ["true", "1", "yes"]
            if include_deleted_param is not None
            else False
        )
        is_active_param = self.request.query_params.get("is_active")
        is_active = None
        if is_active_param is not None:
            if is_active_param.lower() in ["true", "1", "yes"]:
                is_active = True
            elif is_active_param.lower() in ["false", "0", "no"]:
                is_active = False

        qs = FinancialAccountSelector.get_accounts(
            company_id=int(company_id) if company_id else None,
            account_type=account_type,
            include_deleted=include_deleted,
            is_active=is_active,
        )
        return self.isolate_queryset(qs)

    def get_serializer_class(self):
        if self.action == "list":
            return FinancialAccountListSerializer
        if self.action == "retrieve":
            return FinancialAccountDetailSerializer
        if self.action == "create":
            return FinancialAccountCreateSerializer
        if self.action == "update":
            return FinancialAccountUpdateSerializer
        return FinancialAccountDetailSerializer

    @finance_account_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Cuentas financieras obtenidas correctamente.",
            code="FINANCIAL_ACCOUNTS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_account_detail_schema
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Cuenta financiera obtenida.",
            code="FINANCIAL_ACCOUNT_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @finance_account_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.to_dto()
        company_id = getattr(request, "company_id", None) or dto.company_id
        if company_id != dto.company_id:
            from dataclasses import replace
            dto = replace(dto, company_id=company_id)

        account = FinancialAccountService.create_account(dto)
        output = FinancialAccountDetailSerializer(account).data

        return self.success_response(
            message="Cuenta financiera registrada exitosamente.",
            code="FINANCIAL_ACCOUNT_CREATED",
            data=output,
            status_code=status.HTTP_201_CREATED,
        )


    @finance_account_update_schema
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = FinancialAccountService.update_account(
            instance.pk, serializer.to_dto()
        )
        output = FinancialAccountDetailSerializer(account).data

        return self.success_response(
            message="Cuenta financiera actualizada exitosamente.",
            code="FINANCIAL_ACCOUNT_UPDATED",
            data=output,
            status_code=status.HTTP_200_OK,
        )

    @finance_account_delete_schema
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        FinancialAccountService.deactivate_account(instance.pk)

        return self.success_response(
            message="Cuenta financiera desactivada exitosamente.",
            code="FINANCIAL_ACCOUNT_DEACTIVATED",
            data=None,
            status_code=status.HTTP_200_OK,
        )

    @finance_account_restore_schema
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        try:
            account = FinancialAccountService.restore_account(pk)
            output = FinancialAccountDetailSerializer(account).data
            return self.success_response(
                message="Cuenta financiera restaurada exitosamente.",
                code="FINANCIAL_ACCOUNT_RESTORED",
                data=output,
                status_code=status.HTTP_200_OK,
            )
        except FinancialAccountNotFoundException:
            return self.error_response(
                message="Cuenta financiera no encontrada.",
                code="FINANCIAL_ACCOUNT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except FinancialAccountAlreadyExistsException as e:
            return self.error_response(
                message=str(e),
                code="FINANCIAL_ACCOUNT_ALREADY_EXISTS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return self.handle_validation_error(
                e, message="Error al restaurar cuenta financiera."
            )
