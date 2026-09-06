import json
import logging
from concurrent.futures import ThreadPoolExecutor

from django.utils.deprecation import MiddlewareMixin
from django.db import connection

from apps.core.models.audit_log import AuditLog

# Executor global para evitar thread exhaustion
audit_executor = ThreadPoolExecutor(max_workers=5)



logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta peticiones HTTP para registrar un Audit Trail.
    """

    SENSITIVE_KEYS = frozenset(["password", "token", "access", "refresh", "secret"])

    @staticmethod
    def _save_audit_log_async(user_id, method, path, ip_address, user_agent, status_code, payload):
        try:
            AuditLog.objects.create(
                user_id=user_id,
                method=method,
                path=path,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=status_code,
                payload=payload,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"No se pudo guardar el registro de auditoría en background: {e!s}")
        finally:
            connection.close()

    def __call__(self, request):
        payload = {}
        content_type = request.META.get("CONTENT_TYPE", "")

        # Si es multipart/form-data, evitamos leer request.body para no corromper
        # el stream ni romper la carga de archivos en las vistas.
        if "multipart/form-data" in content_type:
            payload = {"detail": "Multipart form data omited."}
        else:
            try:
                body_bytes = request.body
                if body_bytes:
                    body_str = body_bytes.decode("utf-8")
                    if len(body_str) > 4096:
                        payload = {"detail": "Payload too large to log."}
                    else:
                        payload = json.loads(body_str)
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                payload = {}

        masked_payload = self._mask_sensitive_data(payload)

        # Continúa la ejecución normal de la petición (aquí se llama a la vista)
        response = self.get_response(request)

        # Solo guardaremos registro de acciones que mutan datos (se excluye GET, OPTIONS, etc.)
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            # En DRF, request.user se establece a veces tarde o queda en un wrapper.
            # Si el usuario se autenticó, intentaremos obtenerlo.
            user = getattr(request, "user", None)
            if user and not user.is_authenticated:
                user = None

            ip_address = self._get_client_ip(request)

            try:
                user_id = user.id_user if user else None
                audit_executor.submit(
                    self._save_audit_log_async,
                    user_id,
                    request.method,
                    request.path,
                    ip_address,
                    request.META.get("HTTP_USER_AGENT", ""),
                    response.status_code,
                    masked_payload,
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f"No se pudo encolar la tarea de auditoría: {e!s}")

        return response

    def _mask_sensitive_data(self, data, depth=0):
        """
        Enmascara campos sensibles recursivamente dentro del payload.
        """
        if depth > 10:
            return "[Max Depth Reached]"

        if isinstance(data, dict):
            masked = {}
            for k, v in data.items():
                # Comprobamos si la clave contiene palabras sensibles
                if isinstance(k, str) and any(
                    sensible in k.lower() for sensible in self.SENSITIVE_KEYS
                ):
                    masked[k] = "********"
                else:
                    masked[k] = self._mask_sensitive_data(v, depth + 1)
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item, depth + 1) for item in data]
        else:
            return data

    def _get_client_ip(self, request):
        """
        Obtiene la IP real del cliente considerando posibles proxies.
        """
        from django.conf import settings

        trust_x_forwarded_for = getattr(settings, "TRUST_X_FORWARDED_FOR", False)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if trust_x_forwarded_for and x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
