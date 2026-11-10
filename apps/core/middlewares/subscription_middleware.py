from django.http import JsonResponse

from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector


class SubscriptionMiddleware:
    """
    Middleware que verifica el estado de la suscripción del inquilino (Tenant).
    Si la suscripción está vencida (fuera del período de gracia) o cancelada,
    bloquea las operaciones de escritura (POST, PUT, PATCH, DELETE) protegiendo
    la integridad del modelo SaaS, mientras permite lecturas de consulta.
    """

    EXEMPT_PREFIXES = (
        "/api/v1/subscriptions/",
        "/api/v1/companies/",
        "/api/v1/auth/",
        "/api/v1/security/",
        "/health/",
        "/admin/",
        "/api/schema/",
        "/api/docs/",
        "/api/redoc/",
    )

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si la ruta está exenta, no aplica bloqueo
        path = request.path_info
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # Si el método es seguro (solo lectura), siempre permitir
        if request.method in self.SAFE_METHODS:
            return self.get_response(request)

        company = getattr(request, "company", None)
        if company:
            subscription = SubscriptionSelector.get_current_subscription(company)
            # Si tiene suscripción y no es válida (vencida sin gracia o cancelada)
            if subscription and not subscription.is_valid:
                return JsonResponse(
                    {
                        "success": False,
                        "error_code": "SUBSCRIPTION_EXPIRED_OR_SUSPENDED",
                        "message": (
                            "La suscripción de su empresa ha vencido o se encuentra suspendida. "
                            "Por favor regularice su pago en el módulo de suscripciones para continuar realizando operaciones."
                        ),
                        "status": subscription.status,
                        "days_remaining": subscription.days_remaining,
                    },
                    status=403,
                )

        return self.get_response(request)

