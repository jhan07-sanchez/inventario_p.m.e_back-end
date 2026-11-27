from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.subscriptions.selectors.subscription_selector import SubscriptionSelector


class PlanLimitValidatorService:
    """
    Servicio de validación de cuotas, límites y permisos modulares según el Plan de la empresa.
    Previene el sobreconsumo de recursos sin upgrade de suscripción.
    """

    @classmethod
    def validate_can_add_user(cls, company) -> None:
        """
        Valida si la empresa puede registrar o asociar un nuevo usuario según su plan.
        Lanza ValidationError con código HTTP 400 si se superó el límite.
        """
        if not company:
            return

        metrics = SubscriptionSelector.get_company_usage_metrics(company)
        usage = metrics.get("usage", {}).get("users", {})
        current = usage.get("current", 0)
        max_allowed = usage.get("max", 1)

        if current >= max_allowed:
            raise ValidationError(
                detail={
                    "error": "PLAN_USER_LIMIT_EXCEEDED",
                    "message": f"Ha alcanzado el límite máximo de usuarios ({max_allowed}) permitido por su plan actual.",
                    "current": current,
                    "max": max_allowed,
                }
            )

    @classmethod
    def validate_can_add_product(cls, company) -> None:
        """
        Valida si la empresa puede crear un nuevo producto en su catálogo.
        Lanza ValidationError con código HTTP 400 si se superó el límite.
        """
        if not company:
            return

        metrics = SubscriptionSelector.get_company_usage_metrics(company)
        usage = metrics.get("usage", {}).get("products", {})
        current = usage.get("current", 0)
        max_allowed = usage.get("max", 100)

        if current >= max_allowed:
            raise ValidationError(
                detail={
                    "error": "PLAN_PRODUCT_LIMIT_EXCEEDED",
                    "message": f"Ha alcanzado el límite máximo de productos ({max_allowed}) permitido por su plan actual.",
                    "current": current,
                    "max": max_allowed,
                }
            )

    @classmethod
    def validate_can_issue_invoice(cls, company) -> None:
        """
        Valida si la empresa puede emitir una factura en el mes actual.
        """
        if not company:
            return

        metrics = SubscriptionSelector.get_company_usage_metrics(company)
        usage = metrics.get("usage", {}).get("invoices", {})
        current = usage.get("current", 0)
        max_allowed = usage.get("max", 100)

        if current >= max_allowed:
            raise ValidationError(
                detail={
                    "error": "PLAN_INVOICE_LIMIT_EXCEEDED",
                    "message": f"Ha alcanzado el límite mensual de facturación ({max_allowed}) permitido por su plan actual.",
                    "current": current,
                    "max": max_allowed,
                }
            )

    @classmethod
    def validate_module_access(cls, company, module_code: str) -> None:
        """
        Verifica si la empresa tiene habilitado el módulo en su plan contratado.
        Si no lo tiene contratado, lanza PermissionDenied (HTTP 403).
        """
        if not company:
            return

        from apps.subscriptions.services.company_entitlement_service import (
            CompanyEntitlementService,
        )

        if not CompanyEntitlementService.is_module_enabled(company, module_code):
            sub = SubscriptionSelector.get_current_subscription(company)
            plan_name = sub.plan.name if sub and sub.plan else "Sin Plan"
            raise PermissionDenied(
                detail={
                    "error": "MODULE_NOT_IN_PLAN",
                    "message": f"El módulo '{module_code}' no está incluido en su plan ({plan_name}). Actualice su suscripción.",
                    "module": module_code,
                    "plan": plan_name,
                }
            )

    @classmethod
    def validate_can_write(cls, company) -> None:
        """
        Valida que la empresa tenga una suscripción que autorice operaciones de escritura.
        Si la suscripción está vencida, cancelada o inactiva, lanza PermissionDenied (HTTP 403).
        """
        if not company:
            return

        sub = SubscriptionSelector.get_current_subscription(company)
        if not sub or not sub.can_write:
            status_name = (
                "EXPIRED"
                if (sub and sub.is_expired)
                else (sub.status if sub else "NO_SUBSCRIPTION")
            )
            raise PermissionDenied(
                detail={
                    "success": False,
                    "code": "SUBSCRIPTION_EXPIRED",
                    "error_code": "SUBSCRIPTION_EXPIRED",
                    "message": "Tu suscripción ha vencido. Tu cuenta está en modo lectura.",
                    "data": {
                        "status": status_name,
                        "is_read_only": True,
                        "can_write": False,
                        "renew_url": "/saas-admin/planes",
                    },
                }
            )
