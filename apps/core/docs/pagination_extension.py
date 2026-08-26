from drf_spectacular.extensions import OpenApiPaginationExtension
from rest_framework import serializers

from apps.core.docs.api_response_schema import build_api_response_schema


class CustomPaginationExtension(OpenApiPaginationExtension):
    """
    Extensión para DRF Spectacular para documentar correctamente la
    clase de paginación 'CustomPagination' del proyecto inventario-pme.
    """

    target_class = "apps.core.pagination.custom_pagination.CustomPagination"

    def get_paginated_response_schema(self, schema):
        # Creamos un serializer interno para los datos de paginación
        PaginationDataSerializer = type(
            "PaginationDataSerializer",
            (serializers.Serializer,),
            {
                "count": serializers.IntegerField(),
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "page": serializers.IntegerField(),
                "total_pages": serializers.IntegerField(),
                "page_size": serializers.IntegerField(),
                "results": schema,
            },
        )

        # Obtenemos un nombre genérico basado en el modelo paginado (si está disponible en schema)
        schema_name = (
            getattr(schema, "name", "Generic") if hasattr(schema, "name") else "Generic"
        )

        return build_api_response_schema(
            name=f"Paginated{schema_name}Response",
            data_serializer=PaginationDataSerializer,
            description="Respuesta paginada estándar.",
        )
