from django.apps import apps
from rest_framework import status

from apps.core.docs.history_docs import history_list_schema
from apps.core.security import HasPermission
from apps.core.serializers.history_serializer import (
    ConfigurationAuditHistorySerializer,
    GenericHistorySerializer,
)
from apps.core.views.base_viewset import BaseGenericViewSet
from apps.users.permissions import IsAuthenticatedAndActive


class SystemHistoryViewSet(BaseGenericViewSet):
    """
    Endpoint unificado para consultar el historial de auditoría de los modelos del ERP.
    Uso: GET /api/v1/history/?model=user
    Uso con filtro de objeto: GET /api/v1/history/?model=user&object_id=1
    """

    permission_classes = [IsAuthenticatedAndActive, HasPermission("settings.view")]
    serializer_class = GenericHistorySerializer

    # Mapa de modelos permitidos para consulta histórica
    ALLOWED_MODELS = {
        "user": "users.User",
        "role": "users.Role",
        "userrole": "users.UserRole",
        "parameter": "configuration.GlobalParameter",
        "globalparameter": "configuration.GlobalParameter",
    }

    @history_list_schema
    def list(self, request, *args, **kwargs):
        model_name = request.query_params.get("model", "").strip().lower()

        # 1. Validar parámetro obligatorio
        if not model_name:
            return self.error_response(
                message="Debe especificar el parámetro 'model' (ej. ?model=user).",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Validar que el modelo pertenezca a la lista blanca permitida
        if model_name not in self.ALLOWED_MODELS:
            return self.error_response(
                message=f"El modelo '{model_name}' no está configurado para auditoría.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 3. Delegación transparente para parámetros globales (ConfigurationAudit)
        if model_name in ("parameter", "globalparameter"):
            from apps.configuration.models import ConfigurationAudit

            audit_qs = (
                ConfigurationAudit.objects.all()
                .select_related("user", "parameter")
                .order_by("-created_at")
            )
            object_id = request.query_params.get("object_id")
            if object_id:
                audit_qs = audit_qs.filter(parameter_id=object_id)

            page = self.paginate_queryset(audit_qs)
            if page is not None:
                serializer = ConfigurationAuditHistorySerializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = ConfigurationAuditHistorySerializer(audit_qs, many=True)
            return self.success_response(
                message="Historial obtenido correctamente.",
                code="HISTORY_FETCHED",
                data=serializer.data,
            )

        # 4. Resolver el modelo de simple_history dinámicamente
        app_label, model_class_name = self.ALLOWED_MODELS[model_name].split(".")
        model = apps.get_model(app_label, model_class_name)

        # 5. Verificar que tenga historial activo
        if not hasattr(model, "history"):
            return self.error_response(
                message="El modelo solicitado no tiene historial habilitado.",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 6. Consultar historial optimizado
        queryset = (
            model.history.all().select_related("history_user").order_by("-history_date")
        )

        # 7. Filtro opcional por ID de objeto (dinámico según la PK real del modelo)
        object_id = request.query_params.get("object_id")
        if object_id:
            original_pk = model._meta.pk.name
            queryset = queryset.filter(**{original_pk: object_id})

        # 8. Paginación y respuesta estandarizada
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Historial obtenido correctamente.",
            code="HISTORY_FETCHED",
            data=serializer.data,
        )

