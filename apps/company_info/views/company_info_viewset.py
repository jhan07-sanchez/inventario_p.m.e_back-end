from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser

from apps.company_info.docs.company_info_docs import (
    company_info_create_schema,
    company_info_current_schema,
    company_info_delete_schema,
    company_info_detail_schema,
    company_info_list_schema,
    company_info_partial_update_schema,
    company_info_update_schema,
    company_info_upload_logo_schema,
)
from apps.company_info.models import CompanyInfo
from apps.company_info.selectors.company_info_selector import CompanyInfoSelector
from apps.company_info.serializers.company_info_serializer import (
    CompanyInfoCreateSerializer,
    CompanyInfoSerializer,
    CompanyInfoUpdateSerializer,
)
from apps.company_info.services.company_info_service import CompanyInfoService
from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseViewSet
from apps.users.permissions import IsAuthenticatedAndActive


class CompanyInfoViewSet(BaseViewSet):
    """
    ViewSet encargado de administrar la información de la empresa.
    """

    queryset = CompanyInfo.objects.all()
    permission_classes = [IsAuthenticatedAndActive]

    def get_permissions(self):
        """
        Retorna los permisos requeridos según la acción.
        """
        permission_map = {
            "list": (
                IsAuthenticatedAndActive,
                HasPermission("settings.view"),
            ),
            "retrieve": (
                IsAuthenticatedAndActive,
                HasPermission("settings.view"),
            ),
            "current": (
                IsAuthenticatedAndActive,
                # Cualquier usuario autenticado debería poder ver la info actual
                # para reportes o tickets, pero limitamos a view si es necesario
                HasPermission("settings.view"),
            ),
            "create": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
            "update": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
            "partial_update": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
            "destroy": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
            "upload_logo": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
            "remove_logo": (
                IsAuthenticatedAndActive,
                HasPermission("settings.update"),
            ),
        }

        classes = permission_map.get(
            self.action,
            (
                IsAuthenticatedAndActive,
                HasPermission("settings.view"),
            ),
        )

        return [permission() for permission in classes]

    def get_queryset(self):
        """
        Retorna el queryset.
        """
        return CompanyInfoSelector.get_all()

    def get_serializer_class(self):
        """
        Retorna el serializer correspondiente según la acción.
        """
        if self.action == "create":
            return CompanyInfoCreateSerializer
        if self.action in ("update", "partial_update"):
            return CompanyInfoUpdateSerializer
        return CompanyInfoSerializer

    @company_info_list_schema
    def list(self, request, *args, **kwargs):
        """
        Lista la información de la empresa (singleton).
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Información de empresa obtenida correctamente.",
            code="COMPANY_INFO_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @company_info_detail_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Obtiene el detalle de una empresa por ID.
        """
        company = CompanyInfoSelector.get_by_id(kwargs["pk"])
        if not company:
            return self.error_response(
                message="Empresa no encontrada.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(company)
        return self.success_response(
            message="Información de empresa obtenida correctamente.",
            code="COMPANY_INFO_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @company_info_current_schema
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """
        Obtiene la información de la empresa activa.
        """
        company = CompanyInfoSelector.get_current()
        if not company:
            return self.error_response(
                message="No hay empresa configurada en el sistema.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(company)
        return self.success_response(
            message="Información de empresa actual obtenida correctamente.",
            code="COMPANY_INFO_FETCHED",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @company_info_create_schema
    def create(self, request, *args, **kwargs):
        """
        Crea el registro de empresa (singleton).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            company = CompanyInfoService.create_company_info(serializer.to_dto())
            response_serializer = CompanyInfoSerializer(company, context={"request": request})
            return self.success_response(
                message="Información de empresa creada correctamente.",
                code="COMPANY_INFO_CREATED",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible crear la empresa.",
            )

    @company_info_update_schema
    def update(self, request, *args, **kwargs):
        """
        Actualiza completamente la empresa.
        """
        company = CompanyInfoSelector.get_by_id(kwargs["pk"])
        if not company:
            return self.error_response(
                message="Empresa no encontrada.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(company, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            company = CompanyInfoService.update_company_info(company, serializer.to_dto())
            response_serializer = CompanyInfoSerializer(company, context={"request": request})
            return self.success_response(
                message="Información de empresa actualizada correctamente.",
                code="COMPANY_INFO_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la empresa.",
            )

    @company_info_partial_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente la empresa.
        """
        company = CompanyInfoSelector.get_by_id(kwargs["pk"])
        if not company:
            return self.error_response(
                message="Empresa no encontrada.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            company = CompanyInfoService.update_company_info(company, serializer.to_dto())
            response_serializer = CompanyInfoSerializer(company, context={"request": request})
            return self.success_response(
                message="Información de empresa actualizada parcialmente.",
                code="COMPANY_INFO_PARTIAL_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible actualizar la empresa.",
            )

    @company_info_delete_schema
    def destroy(self, request, *args, **kwargs):
        """
        Desactiva lógicamente la empresa.
        """
        company = CompanyInfoSelector.get_by_id(kwargs["pk"])
        if not company:
            return self.error_response(
                message="Empresa no encontrada.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            CompanyInfoService.deactivate_company_info(company)
            return self.success_response(
                message="Información de empresa desactivada correctamente.",
                code="COMPANY_INFO_DELETED",
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as exception:
            return self.handle_validation_error(
                exception,
                message="No fue posible desactivar la empresa.",
            )

    @company_info_upload_logo_schema
    @action(detail=True, methods=["post"], url_path="upload-logo", parser_classes=[MultiPartParser])
    def upload_logo(self, request, pk=None):
        """
        Sube o actualiza el logo de la empresa.
        """
        company = CompanyInfoSelector.get_by_id(pk)
        if not company:
            return self.error_response(
                message="Empresa no encontrada.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logo_file = request.FILES.get("logo")
        if not logo_file:
            return self.error_response(
                message="No se proporcionó ningún archivo de logo.",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            company = CompanyInfoService.update_logo(company, logo_file)
            response_serializer = CompanyInfoSerializer(company, context={"request": request})
            return self.success_response(
                message="Logo actualizado correctamente.",
                code="COMPANY_INFO_LOGO_UPDATED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            return self.error_response(
                message=f"Error al subir el logo: {str(e)}",
                code="INTERNAL_SERVER_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["delete"], url_path="remove-logo")
    def remove_logo(self, request, pk=None):
        """
        Elimina el logo de la empresa.
        """
        company = CompanyInfoSelector.get_by_id(pk)
        if not company:
            return self.error_response(
                message="Empresa no encontrada.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            company = CompanyInfoService.remove_logo(company)
            response_serializer = CompanyInfoSerializer(company, context={"request": request})
            return self.success_response(
                message="Logo eliminado correctamente.",
                code="COMPANY_INFO_LOGO_REMOVED",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            return self.error_response(
                message=f"Error al eliminar el logo: {str(e)}",
                code="INTERNAL_SERVER_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
