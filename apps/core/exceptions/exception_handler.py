import logging

from django.core.exceptions import (
    ObjectDoesNotExist,
)
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.exceptions.custom_exceptions import BusinessException
from apps.core.exceptions.error_codes import ErrorCodes

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Manejador global de excepciones para toda la API.

    Convierte todas las excepciones conocidas en un formato uniforme.
    """

    response = exception_handler(exc, context)

    # ==========================================================
    # Excepciones de Django (fuera de DRF)
    # ==========================================================
    if response is None:
        if isinstance(exc, DjangoValidationError):
            errors = exc.message_dict if hasattr(exc, "message_dict") else exc.messages

            return Response(
                {
                    "success": False,
                    "code": ErrorCodes.VALIDATION_ERROR,
                    "message": "Error de validación.",
                    "data": None,
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(exc, ObjectDoesNotExist):
            return Response(
                {
                    "success": False,
                    "code": ErrorCodes.NOT_FOUND,
                    "message": "Recurso no encontrado.",
                    "data": None,
                    "errors": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        logger.error(f"Error interno: {exc}", exc_info=True)
        return Response(
            {
                "success": False,
                "code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "Ha ocurrido un error interno en el servidor.",
                "data": None,
                "errors": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ==========================================================
    # Excepciones de negocio
    # ==========================================================
    if isinstance(exc, BusinessException):
        extra_data = getattr(exc, "extra_data", None)
        response.data = {
            "success": False,
            "code": exc.default_code,
            "message": str(exc.detail),
            "data": None,
            "errors": None,
        }
        if extra_data is not None:
            response.data["meta"] = extra_data

        return response

    # ==========================================================
    # Excepciones de DRF
    # ==========================================================
    message = "Ha ocurrido un error."
    error_code = ErrorCodes.INTERNAL_SERVER_ERROR

    if isinstance(exc, ValidationError):
        message = "Error de validación."
        error_code = ErrorCodes.VALIDATION_ERROR

    elif isinstance(exc, AuthenticationFailed):
        message = "Credenciales inválidas."
        error_code = ErrorCodes.AUTHENTICATION_FAILED

    elif isinstance(exc, NotAuthenticated):
        message = "No autenticado."
        error_code = ErrorCodes.AUTHENTICATION_FAILED

    elif isinstance(exc, PermissionDenied):
        message = "No tiene permisos para realizar esta acción."
        error_code = ErrorCodes.PERMISSION_DENIED

    elif isinstance(exc, (NotFound, Http404)):
        message = "Recurso no encontrado."
        error_code = ErrorCodes.NOT_FOUND

    response.data = {
        "success": False,
        "code": error_code,
        "message": message,
        "data": None,
        "errors": response.data,
    }

    return response
