from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.users.permissions import IsAuthenticatedAndActive

from apps.cash.docs.cash_docs import (
    cash_session_add_movement_schema,
    cash_session_close_schema,
    cash_session_current_schema,
    cash_session_detail_schema,
    cash_session_list_schema,
    cash_session_movements_schema,
    cash_session_open_schema,
)
from apps.cash.models.cash_session import CashSession
from apps.cash.selectors.cash_session_selector import CashSessionSelector
from apps.cash.serializers.cash_session_serializer import (
    CashSessionRetrieveSerializer,
    CashSessionOpenSerializer,
    CashSessionCloseSerializer
)
from apps.cash.serializers.cash_movement_serializer import (
    CashMovementRetrieveSerializer,
    CashMovementCreateSerializer
)
from apps.cash.services.cash_session_service import CashSessionService
from apps.cash.services.cash_movement_service import CashMovementService


class CashSessionViewSet(BaseGenericViewSet):
    """
    ViewSet para manejar la apertura, cierre y movimientos manuales de caja.
    """
    http_method_names = ["get", "post", "head", "options"]
    queryset = CashSession.objects.none()
    permission_classes = [IsAuthenticatedAndActive]

    def get_permissions(self):
        permission_map = {
            "list": (IsAuthenticatedAndActive, HasPermission("cash.view")),
            "retrieve": (IsAuthenticatedAndActive, HasPermission("cash.view")),
            "open": (IsAuthenticatedAndActive, HasPermission("cash.open")),
            "close": (IsAuthenticatedAndActive, HasPermission("cash.close")),
            "current": (IsAuthenticatedAndActive, HasPermission("cash.view")),
            "add_movement": (IsAuthenticatedAndActive, HasPermission("cash.movement")),
            "movements": (IsAuthenticatedAndActive, HasPermission("cash.view")),
        }
        classes = permission_map.get(self.action, (IsAuthenticatedAndActive, HasPermission("cash.view")))
        return [permission() for permission in classes]

    def get_queryset(self):
        return CashSessionSelector.get_all()

    def get_serializer_class(self):
        if self.action == "open":
            return CashSessionOpenSerializer
        if self.action == "close":
            return CashSessionCloseSerializer
        if self.action == "add_movement":
            return CashMovementCreateSerializer
        return CashSessionRetrieveSerializer

    @cash_session_list_schema
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Sesiones obtenidas.",
            code="CASH_SESSIONS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @cash_session_detail_schema
    def retrieve(self, request, *args, **kwargs):
        session = CashSessionSelector.get_by_id(kwargs["pk"])
        serializer = self.get_serializer(session)
        return self.success_response(
            message="Sesión obtenida.",
            code="CASH_SESSION_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @cash_session_current_schema
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        session = CashSessionSelector.get_current_session(request.user)
        if not session:
            return self.error_response(
                message="No tienes una sesión de caja abierta.",
                code="NO_OPEN_SESSION",
                status_code=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(session)
        return self.success_response(
            message="Sesión actual obtenida.",
            code="CURRENT_SESSION_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @cash_session_open_schema
    @action(detail=False, methods=["post"], url_path="open")
    def open(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session = CashSessionService.open_session(serializer.to_dto(), request.user)
            response_serializer = CashSessionRetrieveSerializer(session)
            return self.success_response(
                message="Sesión abierta correctamente.",
                code="CASH_SESSION_OPENED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return self.handle_validation_error(e, "Error al abrir sesión de caja.")

    @cash_session_close_schema
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        session = CashSessionSelector.get_by_id(pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session = CashSessionService.close_session(session, serializer.to_dto())
            response_serializer = CashSessionRetrieveSerializer(session)
            return self.success_response(
                message="Sesión cerrada correctamente.",
                code="CASH_SESSION_CLOSED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValidationError as e:
            return self.handle_validation_error(e, "Error al cerrar sesión de caja.")

    @cash_session_add_movement_schema
    @action(detail=True, methods=["post"], url_path="movements")
    def add_movement(self, request, pk=None):
        session = CashSessionSelector.get_by_id(pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movement = CashMovementService.create_movement(serializer.to_dto(session.id_cash_session))
            response_serializer = CashMovementRetrieveSerializer(movement)
            return self.success_response(
                message="Movimiento registrado correctamente.",
                code="CASH_MOVEMENT_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return self.handle_validation_error(e, "Error al registrar movimiento.")

    @cash_session_movements_schema
    @action(detail=True, methods=["get"], url_path="movements/list")
    def movements(self, request, pk=None):
        session = CashSessionSelector.get_by_id(pk)
        movements = CashSessionSelector.get_movements(session.id_cash_session)
        serializer = CashMovementRetrieveSerializer(movements, many=True)
        return self.success_response(
            message="Movimientos obtenidos correctamente.",
            code="CASH_MOVEMENTS_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
