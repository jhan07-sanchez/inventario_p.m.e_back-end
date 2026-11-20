from rest_framework import status
from rest_framework.decorators import action

from apps.core.pagination.custom_pagination import CustomPagination
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.saas_admin.permissions import IsSaaSSuperuser
from apps.saas_admin.selectors.team_selector import SaaSTeamSelector
from apps.saas_admin.serializers.team_serializer import (
    SaaSTeamCreateSerializer,
    SaaSTeamDetailSerializer,
    SaaSTeamListSerializer,
    SaaSTeamUpdateSerializer,
)
from apps.saas_admin.services.team_service import SaaSTeamService


class SaaSTeamViewSet(BaseGenericViewSet):
    """
    ViewSet administrativo para la gestión del personal interno de la plataforma SaaS.
    Permite listar, crear, modificar perfiles y activar/desactivar accesos del equipo.
    Protegido estrictamente por el permiso IsSaaSSuperuser (solo Propietario / Superadministrador).
    """

    permission_classes = [IsSaaSSuperuser]
    pagination_class = CustomPagination
    serializer_class = SaaSTeamListSerializer

    def list(self, request, *args, **kwargs):
        """Lista a los integrantes del equipo SaaS con filtros y paginación."""
        search = request.query_params.get("search")
        profile = request.query_params.get("profile")
        is_active_param = request.query_params.get("is_active")

        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")

        qs = SaaSTeamSelector.get_team_members(
            search=search,
            saas_profile=profile,
            is_active=is_active,
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SaaSTeamListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SaaSTeamListSerializer(qs, many=True)
        return self.success_response(
            data=serializer.data,
            code="SAAS_TEAM_FETCHED",
            message="Miembros del equipo obtenidos correctamente.",
        )

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Obtiene el detalle completo y traza de actividad de un integrante."""
        member = SaaSTeamSelector.get_team_member_by_id(user_id=int(pk))
        if not member:
            return self.error_response(
                message="Integrante del equipo no encontrado.",
                code="TEAM_MEMBER_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = SaaSTeamDetailSerializer(member)
        return self.success_response(
            data=serializer.data,
            code="SAAS_TEAM_DETAIL_FETCHED",
            message="Detalle del integrante obtenido correctamente.",
        )

    def create(self, request, *args, **kwargs):
        """Registra un nuevo integrante en el equipo interno SaaS."""
        serializer = SaaSTeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = SaaSTeamService.create_member(
            data=serializer.validated_data,
            actor_user=request.user,
        )

        resp_serializer = SaaSTeamDetailSerializer(user)
        return self.success_response(
            data=resp_serializer.data,
            code="SAAS_TEAM_MEMBER_CREATED",
            message="Integrante del equipo registrado correctamente.",
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None, *args, **kwargs):
        """Actualiza la información o perfil de un integrante."""
        serializer = SaaSTeamUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = SaaSTeamService.update_member(
            user_id=int(pk),
            data=serializer.validated_data,
            actor_user=request.user,
        )

        resp_serializer = SaaSTeamDetailSerializer(user)
        return self.success_response(
            data=resp_serializer.data,
            code="SAAS_TEAM_MEMBER_UPDATED",
            message="Integrante actualizado correctamente.",
        )

    def partial_update(self, request, pk=None, *args, **kwargs):
        return self.update(request, pk, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="roles")
    def roles(self, request):
        """Consulta los perfiles y roles disponibles para el equipo interno."""
        catalog = SaaSTeamSelector.get_available_roles()
        return self.success_response(
            data=catalog,
            code="SAAS_ROLES_FETCHED",
            message="Roles disponibles obtenidos correctamente.",
        )

    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        """Activa o desactiva (revoca acceso) a un integrante."""
        is_active = request.data.get("is_active")
        if is_active is None:
            return self.error_response(
                message="El parámetro 'is_active' (booleano) es requerido.",
                code="IS_ACTIVE_REQUIRED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        is_active_bool = bool(is_active)
        user = SaaSTeamService.toggle_status(
            user_id=int(pk),
            is_active=is_active_bool,
            actor_user=request.user,
        )

        return self.success_response(
            data={
                "id_user": user.id_user,
                "is_active": user.is_active,
            },
            code="SAAS_TEAM_STATUS_UPDATED",
            message=f"Estado del integrante actualizado a {'Activo' if user.is_active else 'Inactivo'}.",
        )
