import logging
import re

from django.utils.deprecation import MiddlewareMixin

from apps.company_info.models import CompanyInfo
from apps.core.context import reset_current_company_id, set_current_company_id

logger = logging.getLogger(__name__)


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware encargado de interceptar el contexto de la Empresa (Tenant).
    Identifica la empresa activa mediante el encabezado HTTP 'X-Company-ID',
    valida la membresía del usuario autenticado y asocia `request.company` y `request.company_id`.
    """

    EXEMPT_PATHS = [
        re.compile(r"^/api/v1/auth/"),
        re.compile(r"^/api/v1/system/"),
        re.compile(r"^/api/v1/companies/my-companies/"),
        re.compile(r"^/api/docs/"),
        re.compile(r"^/api/schema/"),
        re.compile(r"^/health/"),
        re.compile(r"^/admin/"),
        re.compile(r"^/static/"),
        re.compile(r"^/media/"),
    ]

    def _is_exempt(self, path: str) -> bool:
        return any(pattern.match(path) for pattern in self.EXEMPT_PATHS)

    def process_request(self, request):
        request.company = None
        request.company_id = None
        request.membership = None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            # Soporte para pruebas con force_authenticate de DRF
            force_user = getattr(request, "_force_auth_user", None)
            if force_user and force_user.is_authenticated:
                user = force_user
                request.user = user

        if not user or not user.is_authenticated:
            # En Django REST Framework, JWT se autentica a menudo dentro de la vista.
            # Decodificamos el token si viene en Authorization Bearer para tener request.user en el middleware.
            auth_header = request.META.get("HTTP_AUTHORIZATION")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    from rest_framework_simplejwt.authentication import JWTAuthentication

                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(
                        auth_header.split(" ")[1].strip()
                    )
                    user = jwt_auth.get_user(validated_token)
                    request.user = user
                except Exception:
                    user = None

        if not user or not user.is_authenticated:
            return None

        header_company_id = request.META.get("HTTP_X_COMPANY_ID")
        company_id = None

        if header_company_id:
            try:
                company_id = int(str(header_company_id).strip())
            except (ValueError, TypeError):
                company_id = None

        from apps.users.models import CompanyMembership

        if company_id is not None:
            if getattr(user, "is_superuser", False):
                company = CompanyInfo.objects.filter(pk=company_id, is_active=True).first()
                if company:
                    request.company = company
                    request.company_id = company.pk
                    request._tenant_token = set_current_company_id(request.company_id)
                else:
                    request._tenant_token = set_current_company_id(None)
                return None

            membership = (
                CompanyMembership.objects.filter(
                    user=user,
                    company_id=company_id,
                    is_active=True,
                    status=CompanyMembership.MembershipStatus.ACTIVE,
                    company__is_active=True,
                )
                .select_related("company", "role")
                .first()
            )

            if membership:
                request.company = membership.company
                request.company_id = membership.company_id
                request.membership = membership
                request._tenant_token = set_current_company_id(request.company_id)
                return None

            # Si el usuario solicitó explícitamente un company_id al cual no tiene acceso y la ruta no es exenta:
            if not self._is_exempt(request.path):
                from django.http import JsonResponse

                return JsonResponse(
                    {
                        "ok": False,
                        "success": False,
                        "status": 403,
                        "code": "TENANT_ACCESS_DENIED",
                        "message": "No tiene acceso a la empresa solicitada o su membresía se encuentra inactiva.",
                        "data": None,
                        "errors": {
                            "company": ["No pertenece a esta organización o membresía inactiva."]
                        },
                    },
                    status=403,
                )

        # Si no envió X-Company-ID, intentamos resolver por empresa única si el usuario tiene exactamente 1
        memberships = CompanyMembership.objects.filter(
            user=user,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
            company__is_active=True,
        ).select_related("company", "role")

        count = memberships.count()
        if count == 1:
            single = memberships.first()
            request.company = single.company
            request.company_id = single.company_id
            request.membership = single

        if getattr(request, "company_id", None) is not None:
            request._tenant_token = set_current_company_id(request.company_id)
        else:
            request._tenant_token = set_current_company_id(None)

        return None

    def process_response(self, request, response):
        if hasattr(request, "_tenant_token"):
            try:
                reset_current_company_id(request._tenant_token)
            except Exception:
                pass
        return response
