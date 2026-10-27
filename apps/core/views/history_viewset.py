from django.apps import apps
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.docs.history_docs import history_list_schema
from apps.core.security import HasPermission
from apps.core.serializers.history_serializer import GenericHistorySerializer
from apps.users.permissions import IsAuthenticatedAndActive


class SystemHistoryViewSet(viewsets.GenericViewSet):
    """
    Endpoint unificado para consultar el historial de cualquier modelo.
    Uso: GET /api/v1/history/?model=user
    """

    permission_classes = [IsAuthenticatedAndActive, HasPermission("settings.view")]
    serializer_class = GenericHistorySerializer

    # 🗺️ Mapa de modelos permitidos (Fácil de escalar)
    ALLOWED_MODELS = {
        "user": "users.User",
        "role": "users.Role",
        "userrole": "users.UserRole",
        # "product": "products.Product",  #Descomentar cuando se implemente historial en productos y ventas
        # "sale": "sales.Sale",
    }
    @history_list_schema
    def list(self, request, *args, **kwargs):
        model_name = request.query_params.get("model", "").lower()

        # 1. Validar parámetro
        if not model_name:
            return Response(
                {"error": "Debe especificar el parámetro 'model' (ej. ?model=user)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Validar modelo permitido
        if model_name not in self.ALLOWED_MODELS:
            return Response(
                {
                    "error": f"El modelo '{model_name}' no está configurado para auditoría."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Resolver el modelo dinámicamente
        app_label, model_class_name = self.ALLOWED_MODELS[model_name].split(".")
        model = apps.get_model(app_label, model_class_name)

        # 4. Verificar que tenga historial activo
        if not hasattr(model, "history"):
            return Response(
                {"error": "El modelo solicitado no tiene historial habilitado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5. Consultar historial optimizado
        queryset = (
            model.history.all().select_related("history_user").order_by("-history_date")
        )

        # 6. Filtro opcional por ID de objeto (?object_id=5)
        object_id = request.query_params.get("object_id")
        if object_id:
            queryset = queryset.filter(id=object_id)

        # 7. Paginación
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
