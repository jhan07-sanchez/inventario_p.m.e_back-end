import logging

from django.http import JsonResponse

from apps.core.exceptions.error_codes import ErrorCodes
from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector

logger = logging.getLogger(__name__)


class SubscriptionMiddleware:
    """
    Middleware que verifica el estado de la suscripción del inquilino (Tenant)
    y valida el acceso a los módulos contratados en el plan (Entitlements).

    Arquitectura de Seguridad: FAIL-CLOSED
    --------------------------------------
    1. Si una ruta del API (/api/v1/) no corresponde a un prefijo exento, ni a un módulo comercial
       mapeado, ni a la lista blanca de rutas de administración/sistema permitidas, se bloquea
       inmediatamente con HTTP 500 (MODULE_MAPPING_ERROR) para alertar al equipo de ingeniería.
    2. Si el endpoint pertenece a un módulo comercial no contratado en el plan activo de la empresa,
       bloquea el acceso con HTTP 403 (MODULE_NOT_IN_PLAN).
    3. Si la suscripción está vencida (fuera del período de gracia) o cancelada, bloquea las
       operaciones de escritura (POST, PUT, PATCH, DELETE), permitiendo únicamente consultas
       seguras (GET, HEAD, OPTIONS) sobre los módulos contratados.
    """

    EXEMPT_PREFIXES = (
        "/api/v1/subscriptions",
        "/api/v1/companies",
        "/api/v1/auth",
        "/api/v1/security",
        "/api/v1/saas-admin",
        "/api/v1/notifications",
        "/health",
        "/admin",
        "/api/schema",
        "/api/docs",
        "/api/redoc",
    )

    ALLOWLISTED_UNMAPPED_PATHS = (
        "/api/v1/users",
        "/api/v1/roles",
        "/api/v1/user-roles",
        "/api/v1/company-info",
        "/api/v1/parameters",
        "/api/v1/audits",
        "/api/v1/versions",
        "/api/v1/configuration",
        "/api/v1/health",
        "/api/v1/system",
        "/api/v1/history",
    )

    PATH_TO_MODULE = (
        ("/api/v1/finance", "finance"),
        ("/api/v1/sales", "sales"),
        ("/api/v1/purchases", "purchases"),
        ("/api/v1/cash-registers", "cash"),
        ("/api/v1/cash-sessions", "cash"),
        ("/api/v1/cash", "cash"),
        ("/api/v1/invoice-templates", "invoices"),
        ("/api/v1/invoices", "invoices"),
        ("/api/v1/inventory-movements", "inventory"),
        ("/api/v1/inventory", "inventory"),
        ("/api/v1/products", "products"),
        ("/api/v1/categories", "categories"),
        ("/api/v1/customers", "customers"),
        ("/api/v1/suppliers", "suppliers"),
    )

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _matches(path: str, prefix: str) -> bool:
        """
        Determina si el path coincide exactamente o es un subpath del prefijo,
        evitando colisiones accidentales de prefijos incompletos.
        """
        clean = prefix.rstrip("/")
        return path == clean or path.startswith(f"{clean}/")

    def __call__(self, request):
        path = request.path_info

        # 1. Si la ruta está en la lista de prefijos exentos, permitir acceso inmediato
        if any(self._matches(path, prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # 2. Identificar si la ruta corresponde a un módulo comercial mapeado
        matching_module = None
        for prefix, module_code in self.PATH_TO_MODULE:
            if self._matches(path, prefix):
                matching_module = module_code
                break

        # 3. FAIL-CLOSED: Si la ruta es del API (/api/v1/) y NO tiene un módulo comercial mapeado
        if matching_module is None and path.startswith("/api/v1/"):
            # Verificar si se trata de una ruta legítima del sistema / identidad
            is_allowlisted = any(
                self._matches(path, prefix) for prefix in self.ALLOWLISTED_UNMAPPED_PATHS
            )
            if not is_allowlisted:
                logger.warning(
                    f"[SubscriptionMiddleware] FAIL-CLOSED: Ruta API comercial sin mapeo de módulo detectada: '{path}'. "
                    f"Método: {request.method}."
                )
                return JsonResponse(
                    {
                        "success": False,
                        "code": ErrorCodes.MODULE_MAPPING_ERROR,
                        "error_code": ErrorCodes.MODULE_MAPPING_ERROR,
                        "message": (
                            "Error interno de configuración: la ruta solicitada no tiene un módulo comercial "
                            "asignado en el sistema de suscripciones. Contacte al equipo de desarrollo."
                        ),
                        "data": None,
                        "errors": None,
                    },
                    status=500,
                )

        # 4. Si la empresa está presente en el contexto del tenant, validar suscripción y entitlements
        company = getattr(request, "company", None)
        if company:
            from apps.subscriptions.services.company_entitlement_service import (
                CompanyEntitlementService,
            )

            # A. Validación de Entitlement Modular: ¿Tiene contratado el módulo en su plan?
            if matching_module:
                if not CompanyEntitlementService.is_module_enabled(company, matching_module):
                    sub = SubscriptionSelector.get_current_subscription(company)
                    plan_name = sub.plan.name if sub and sub.plan else "Sin Plan"
                    return JsonResponse(
                        {
                            "success": False,
                            "code": ErrorCodes.MODULE_NOT_IN_PLAN,
                            "error_code": ErrorCodes.MODULE_NOT_IN_PLAN,
                            "message": (
                                f"El módulo '{matching_module}' no está incluido en el plan de su empresa ({plan_name}). "
                                "Por favor contacte a su administrador o actualice su suscripción."
                            ),
                            "data": {
                                "module": matching_module,
                                "plan": plan_name,
                            },
                            "module": matching_module,
                            "plan": plan_name,
                            "errors": None,
                        },
                        status=403,
                    )

            # B. Si el método es de escritura y la suscripción está vencida o cancelada
            if request.method not in self.SAFE_METHODS:
                subscription = SubscriptionSelector.get_current_subscription(company)
                if subscription and not subscription.is_valid:
                    return JsonResponse(
                        {
                            "success": False,
                            "code": ErrorCodes.SUBSCRIPTION_EXPIRED_OR_SUSPENDED,
                            "error_code": ErrorCodes.SUBSCRIPTION_EXPIRED_OR_SUSPENDED,
                            "message": (
                                "La suscripción de su empresa ha vencido o se encuentra suspendida. "
                                "Por favor regularice su pago en el módulo de suscripciones para continuar realizando operaciones."
                            ),
                            "data": {
                                "status": subscription.status,
                                "days_remaining": subscription.days_remaining,
                            },
                            "status": subscription.status,
                            "days_remaining": subscription.days_remaining,
                            "errors": None,
                        },
                        status=403,
                    )

        return self.get_response(request)
