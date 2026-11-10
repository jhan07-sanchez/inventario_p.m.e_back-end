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

        sub = SubscriptionSelector.get_current_subscription(company)
        if not sub or not sub.plan:
            return

        enabled_modules = sub.plan.enabled_modules or []
        # Si la lista de módulos está vacía, se considera acceso completo por defecto (retrocompatibilidad)
        if not enabled_modules:
            return

        if module_code.lower() not in [m.lower() for m in enabled_modules]:
            raise PermissionDenied(
                detail={
                    "error": "MODULE_NOT_IN_PLAN",
                    "message": f"El módulo '{module_code}' no está incluido en su plan ({sub.plan.name}). Actualice su suscripción.",
                    "module": module_code,
                    "plan": sub.plan.name,
                }
            )

