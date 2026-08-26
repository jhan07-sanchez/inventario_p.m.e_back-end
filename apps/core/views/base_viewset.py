from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from apps.core.utils.api_response import ApiResponse


class BaseViewSet(ModelViewSet):
    """
    ViewSet base para todos los modulos de inventario-pme.

    Centraliza la logica comun utilizada para todos los ViewSets,
    evitando duplicacion de codigo y garantizando respuestas
    standarizadas en todas las API.
    """

    @staticmethod
    def success_response(
        *,
        data=None,
        code="SUCCESS",
        message="Operacion realizada correctamente.",
        status_code=status.HTTP_200_OK,
    ):
        """
        Retorna una respuesta exitosa estandarizada.
        """

        return ApiResponse.success(
            data=data,
            code=code,
            message=message,
            status_code=status_code,
        )

    @staticmethod
    def error_response(
        *,
        message="Ha ocurrido un error.",
        code="ERROR",
        errors=None,
        status_code=status.HTTP_400_BAD_REQUEST,
    ):
        """
        Retorna una respuesta de error estandarizada.
        """

        return ApiResponse.error(
            message=message,
            code=code,
            errors=errors,
            status_code=status_code,
        )

    @staticmethod
    def handler_validation_error(
        exception: ValidationError,
        *,
        message="Error de validacion.",
    ):
        """
        Convierte un ValidationError de Django en una respuesta
        uniforme para toda la API
        """

        errors = (
            exception.message_dict
            if hasattr(exception, "message_dict")
            else exception.messages
        )

        return ApiResponse.error(
            message=message,
            errors=errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    handle_validation_error = handler_validation_error
