from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from apps.core.utils.api_response import ApiResponse


class BaseResponseMixin:
    """
    Mixin con helpers de respuestas estandarizadas para la API.
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
        uniforme para toda la API.
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


class TenantIsolationMixin:
    """
    Mixin central que aplica aislamiento estricto multi-tenant a cualquier ViewSet.
    Garantiza que ninguna consulta exponga datos de otras empresas (prevención de IDOR).
    """

    def _apply_tenant_filter(self, qs, company_id=None, company_ids=None):
        if qs is None:
            return qs
        model = getattr(qs, "model", None)
        if not model:
            return qs

        fields = [f.name for f in model._meta.fields]
        kw = lambda field: {f"{field}__in": company_ids} if company_ids is not None else {f"{field}": company_id}

        # 1. Modelos con relación directa 'company' o 'company_id' (TenantModel)
        if "company" in fields or "company_id" in fields or hasattr(model, "company"):
            return qs.filter(**kw("company_id"))

        # 2. Modelo User (aislado por membresías activas de la empresa)
        if model._meta.app_label == "users" and model.__name__ == "User":
            filter_kwargs = (
                {"memberships__company_id__in": company_ids, "memberships__is_active": True}
                if company_ids is not None
                else {"memberships__company_id": company_id, "memberships__is_active": True}
            )
            return qs.filter(**filter_kwargs).distinct()

        # 3. Modelo UserRole (aislado por membresía de la empresa)
        if model._meta.app_label == "users" and model.__name__ == "UserRole":
            filter_kwargs = (
                {"user__memberships__company_id__in": company_ids, "user__memberships__is_active": True}
                if company_ids is not None
                else {"user__memberships__company_id": company_id, "user__memberships__is_active": True}
            )
            return qs.filter(**filter_kwargs).distinct()

        # 4. Modelo Inventory (aislado a través de product__company_id)
        if model._meta.app_label == "inventory" and model.__name__ == "Inventory":
            return qs.filter(**kw("product__company_id"))

        # 5. Modelo InventoryMovement (aislado a través de inventory__product__company_id)
        if (
            model._meta.app_label == "inventory"
            and model.__name__ == "InventoryMovement"
        ):
            return qs.filter(**kw("inventory__product__company_id"))

        # 6. Modelo SaleDetail (aislado a través de sale__company_id)
        if model._meta.app_label == "sales" and model.__name__ == "SaleDetail":
            return qs.filter(**kw("sale__company_id"))

        # 7. Modelo PurchaseDetail (aislado a través de purchase__company_id)
        if model._meta.app_label == "purchases" and model.__name__ == "PurchaseDetail":
            return qs.filter(**kw("purchase__company_id"))

        # 8. Modelo InvoiceItem (aislado a través de invoice__company_id)
        if model._meta.app_label == "invoices" and model.__name__ == "InvoiceItem":
            return qs.filter(**kw("invoice__company_id"))

        # 9. Modelo CashMovement (aislado a través de cash_session__company_id)
        if model._meta.app_label == "cash" and model.__name__ == "CashMovement":
            return qs.filter(**kw("cash_session__company_id"))

        # 10. Modelo Payment (aislado a través de sale__company_id o cash_movements__cash_session__company_id)
        if model._meta.app_label == "cash" and model.__name__ == "Payment":
            from django.db.models import Q
            if company_ids is not None:
                return qs.filter(
                    Q(sale__company_id__in=company_ids)
                    | Q(cash_movements__cash_session__company_id__in=company_ids)
                ).distinct()
            return qs.filter(
                Q(sale__company_id=company_id)
                | Q(cash_movements__cash_session__company_id=company_id)
            ).distinct()

        # 11. Modelos Financieros indirectos
        if model._meta.app_label == "finance":
            if model.__name__ in ("FinancialMovement", "FinancialReconciliation"):
                return qs.filter(**kw("account__company_id"))
            if model.__name__ == "FinancialTransfer":
                return qs.filter(**kw("source_account__company_id"))

        # 12. Subscriptions Payment
        if (
            model._meta.app_label == "subscriptions"
            and model.__name__ == "SubscriptionPayment"
        ):
            return qs.filter(**kw("subscription__company_id"))

        return qs

    def isolate_queryset(self, qs):
        """
        Aplica aislamiento multi-tenant a un queryset según el modelo y el contexto de la petición.
        """
        if qs is None:
            return qs

        request = getattr(self, "request", None)
        if not request:
            return qs

        user = getattr(request, "user", None)
        company_id = getattr(request, "company_id", None)
        if not company_id and hasattr(request, "company") and request.company:
            company_id = getattr(request.company, "id_company", None) or getattr(
                request.company, "pk", None
            )

        is_superuser = user and getattr(user, "is_superuser", False)

        # Si el usuario es superusuario y no envía header X-Company-ID, puede consultar global
        if is_superuser and not company_id:
            return qs

        # Si tenemos company_id identificado, filtramos estrictamente por esa empresa
        if company_id is not None:
            return self._apply_tenant_filter(qs, company_id=company_id)

        # Si no hay company_id explícito, pero el usuario pertenece a empresas activas, confinamos a sus empresas
        if user and getattr(user, "is_authenticated", False) and hasattr(user, "memberships"):
            user_company_ids = list(
                user.memberships.filter(is_active=True).values_list("company_id", flat=True)
            )
            if user_company_ids:
                return self._apply_tenant_filter(qs, company_ids=user_company_ids)

        # Sin contexto de empresa (ej. pruebas sin multi-tenant, o modelos globales)
        return qs

    @staticmethod
    def _is_tenant_model(model) -> bool:
        if not model:
            return False
        try:
            from apps.core.models.tenant_model import TenantModel

            if issubclass(model, TenantModel):
                return True
        except Exception:
            pass
        fields = [f.name for f in getattr(model._meta, "fields", [])]
        return "company" in fields or "company_id" in fields

    def get_queryset(self):
        qs = super().get_queryset()
        return self.isolate_queryset(qs)

    def filter_queryset(self, queryset):
        qs = self.isolate_queryset(queryset)
        return super().filter_queryset(qs)


class BaseViewSet(TenantIsolationMixin, BaseResponseMixin, ModelViewSet):
    """
    ViewSet base para todos los módulos de inventario-pme (CRUD completo).
    Incorpora aislamiento multi-tenant automático, inyección de contexto empresarial
    y blindaje contra Mass Assignment e IDOR.
    """

    def get_serializer(self, *args, **kwargs):
        """
        Retorna la instancia del serializador asegurando:
        1. Limpieza de campos tenant del payload de entrada (prevención Mass Assignment).
        2. Configuración de 'company' y 'company_id' como read_only.
        3. Inyección automática de company_id en validated_data al validar exitosamente.
        """
        # Sanitizar entrada si el frontend o un atacante envía company o company_id en el cuerpo
        if "data" in kwargs and hasattr(kwargs["data"], "copy"):
            cleaned_data = kwargs["data"].copy()
            if hasattr(cleaned_data, "pop"):
                cleaned_data.pop("company", None)
                cleaned_data.pop("company_id", None)
                kwargs["data"] = cleaned_data

        serializer = super().get_serializer(*args, **kwargs)

        # Blindar campos tenant a nivel de campos del serializador
        if hasattr(serializer, "fields"):
            for fname in ("company", "company_id"):
                if fname in serializer.fields:
                    serializer.fields[fname].read_only = True

        # Inyectar company_id en validated_data para ViewSets que consumen serializer.validated_data
        original_validate = serializer.validate

        def wrapped_validate(attrs):
            validated_attrs = original_validate(attrs)
            company_id = getattr(self.request, "company_id", None)
            if not company_id and hasattr(self.request, "company") and self.request.company:
                company_id = getattr(self.request.company, "id_company", None) or getattr(
                    self.request.company, "pk", None
                )

            model = (
                getattr(serializer.Meta, "model", None)
                if hasattr(serializer, "Meta")
                else None
            )
            if not model and hasattr(self, "queryset") and self.queryset is not None:
                model = getattr(self.queryset, "model", None)

            if self._is_tenant_model(model):
                user = getattr(self.request, "user", None)
                user_has_memberships = (
                    user
                    and getattr(user, "is_authenticated", False)
                    and hasattr(user, "memberships")
                    and user.memberships.filter(is_active=True).exists()
                )
                # Si es una mutación (create/update) y el usuario pertenece a empresas pero no especificó una activa
                if (
                    self.action in ("create", "update", "partial_update")
                    and company_id is None
                    and user_has_memberships
                    and not getattr(user, "is_superuser", False)
                ):
                    raise PermissionDenied(
                        "Se requiere un contexto de empresa activa (encabezado X-Company-ID) para registrar información."
                    )
                if company_id:
                    validated_attrs["company_id"] = company_id
            return validated_attrs

        serializer.validate = wrapped_validate
        return serializer

    def perform_create(self, serializer):
        """
        Inyecta automáticamente la empresa activa al persistir nuevos registros multi-tenant.
        Previene la creación de registros huérfanos o con company_id = NULL.
        """
        model = (
            getattr(serializer.Meta, "model", None)
            if hasattr(serializer, "Meta")
            else None
        )
        if not model and hasattr(self, "queryset") and self.queryset is not None:
            model = getattr(self.queryset, "model", None)

        if self._is_tenant_model(model):
            company_id = getattr(self.request, "company_id", None)
            if not company_id and hasattr(self.request, "company") and self.request.company:
                company_id = getattr(self.request.company, "id_company", None) or getattr(
                    self.request.company, "pk", None
                )

            user = getattr(self.request, "user", None)
            user_has_memberships = (
                user
                and getattr(user, "is_authenticated", False)
                and hasattr(user, "memberships")
                and user.memberships.filter(is_active=True).exists()
            )
            if (
                company_id is None
                and user_has_memberships
                and not getattr(user, "is_superuser", False)
            ):
                raise PermissionDenied(
                    "Se requiere un contexto de empresa activa (encabezado X-Company-ID) para crear este recurso."
                )

            if company_id is not None:
                serializer.save(company_id=company_id)
                return

        serializer.save()

    def perform_update(self, serializer):
        """
        Asegura que las actualizaciones mantengan la empresa asignada y bloquea cualquier
        intento de alteración de pertenencia organizacional (blindaje contra IDOR).
        """
        model = (
            getattr(serializer.Meta, "model", None)
            if hasattr(serializer, "Meta")
            else None
        )
        if not model and hasattr(self, "queryset") and self.queryset is not None:
            model = getattr(self.queryset, "model", None)

        if self._is_tenant_model(model):
            instance = serializer.instance
            existing_company_id = getattr(instance, "company_id", None)
            request_company_id = getattr(self.request, "company_id", None)
            company_id = existing_company_id or request_company_id

            user = getattr(self.request, "user", None)
            user_has_memberships = (
                user
                and getattr(user, "is_authenticated", False)
                and hasattr(user, "memberships")
                and user.memberships.filter(is_active=True).exists()
            )
            if (
                company_id is None
                and user_has_memberships
                and not getattr(user, "is_superuser", False)
            ):
                raise PermissionDenied(
                    "Se requiere un contexto de empresa activa para actualizar este recurso."
                )

            if company_id is not None:
                serializer.save(company_id=company_id)
                return

        serializer.save()


class BaseGenericViewSet(TenantIsolationMixin, BaseResponseMixin, GenericViewSet):
    """
    ViewSet base no opinado para módulos con acciones personalizadas sin CRUD forzado.
    Incorpora aislamiento multi-tenant automático.
    """

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs and hasattr(kwargs["data"], "copy"):
            cleaned_data = kwargs["data"].copy()
            if hasattr(cleaned_data, "pop"):
                cleaned_data.pop("company", None)
                cleaned_data.pop("company_id", None)
                kwargs["data"] = cleaned_data

        serializer = super().get_serializer(*args, **kwargs)

        if hasattr(serializer, "fields"):
            for fname in ("company", "company_id"):
                if fname in serializer.fields:
                    serializer.fields[fname].read_only = True

        return serializer
