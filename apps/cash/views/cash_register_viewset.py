from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.permissions import IsAuthenticatedAndActive
from apps.cash.docs.cash_docs import (
    cash_register_create_schema,
    cash_register_detail_schema,
    cash_register_list_schema,
)
from apps.cash.models.cash_register import CashRegister
from apps.cash.selectors.cash_register_selector import CashRegisterSelector
from apps.cash.serializers.cash_register_serializer import CashRegisterSerializer


class CashRegisterViewSet(BaseViewSet):
    """
    ViewSet para listar y consultar Cajas Registradoras.
    """
    http_method_names = ["get", "post", "head", "options"]
    queryset = CashRegister.objects.none()
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("cash.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("cash.view")),
            "create": (IsAuthenticatedAndActive, HasPermission("cash.create")),
        }
        classes = permission_map.get(self.action, (IsAuthenticatedAndActive, HasPermission("cash.view")))
        return [permission() for permission in classes]

    def get_queryset(self):
        return CashRegisterSelector.get_all()

    def get_serializer_class(self):
        return CashRegisterSerializer

    @cash_register_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Cajas obtenidas correctamente.",
            code="CASH_REGISTERS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @cash_register_detail_schema
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Caja obtenida correctamente.",
            code="CASH_REGISTER_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @cash_register_create_schema
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success_response(
            message="Caja registrada correctamente.",
            code="CASH_REGISTER_CREATED",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )
