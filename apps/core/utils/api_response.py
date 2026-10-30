from rest_framework import status
from rest_framework.response import Response


class ApiResponse:
    """
    Clase utilitaria para estandarizar las respuestas
    de toda la API de inventario-pme
    """

    @staticmethod
    def success(
        data=None,
        code="SUCCESS",
        message="Operacion realizada correctamente.",
        status_code=status.HTTP_200_OK,
    ):
        """
        Retorna una respuesta exitosa.
        """

        return Response(
            {
                "success": True,
                "code": code,
                "message": message,
                "data": data,
                "errors": None,
            },
            status=status_code,
        )

    @staticmethod
    def error(
        message="Ha ocurrido un error.",
        code="ERROR",
        errors=None,
        status_code=status.HTTP_400_BAD_REQUEST,
        meta=None,
    ):
        """
        Retorna una respuesta de error.
        """

        payload = {
            "success": False,
            "code": code,
            "message": message,
            "data": None,
            "errors": errors,
        }
        if meta is not None:
            payload["meta"] = meta

        return Response(
            payload,
            status=status_code,
        )
