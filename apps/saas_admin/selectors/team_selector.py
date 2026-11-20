from typing import Optional
from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.users.models import Role, UserRole

User = get_user_model()


class SaaSTeamSelector:
    """
    Selector centralizado para consultas de lectura sobre el personal y equipo interno del SaaS.
    Filtra estrictamente a usuarios internos (is_staff=True o is_superuser=True),
    garantizando aislamiento de usuarios empresariales de clientes.
    """

    @classmethod
    def get_team_members(
        cls,
        search: Optional[str] = None,
        saas_profile: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> QuerySet[User]:
        """
        Retorna el QuerySet optimizado de los miembros del equipo interno SaaS.
        """
        qs = (
            User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
            .prefetch_related("user_roles__role")
            .order_by("-is_superuser", "id_user")
        )

        if search:
            term = search.strip()
            qs = qs.filter(
                Q(username__icontains=term)
                | Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(email__icontains=term)
                | Q(document_number__icontains=term)
            )

        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        if saas_profile:
            prof = saas_profile.strip().upper()
            if prof == "SUPERADMIN":
                qs = qs.filter(is_superuser=True)
            elif prof == "SUPPORT":
                qs = qs.filter(user_roles__role__role_name__icontains="Soporte")
            elif prof == "SALES":
                qs = qs.filter(user_roles__role__role_name__icontains="Ventas")
            elif prof == "FINANCE":
                qs = qs.filter(user_roles__role__role_name__icontains="Finanzas")

        return qs.distinct()

    @classmethod
    def get_team_member_by_id(cls, user_id: int) -> Optional[User]:
        """
        Retorna un miembro específico del equipo SaaS o None si no existe o no es staff/superuser.
        """
        return (
            User.objects.filter(pk=user_id)
            .filter(Q(is_staff=True) | Q(is_superuser=True))
            .prefetch_related("user_roles__role")
            .first()
        )

    @classmethod
    def get_available_roles(cls) -> list[dict]:
        """
        Retorna el catálogo de perfiles funcionales definidos para el equipo interno.
        """
        return [
            {
                "code": "SUPERADMIN",
                "label": "Propietario / Superadministrador",
                "description": "Control global de la plataforma, gestión de equipo, suscripciones y seguridad.",
                "permissions": ["*"],
            },
            {
                "code": "SUPPORT",
                "label": "Soporte Técnico",
                "description": "Atención de incidencias, impersonación autorizada de empresas y diagnóstico.",
                "permissions": [
                    "saas.dashboard.view",
                    "saas.tenants.view",
                    "saas.tenants.impersonate",
                    "saas.versions.view",
                ],
            },
            {
                "code": "SALES",
                "label": "Ventas y Comercial",
                "description": "Gestión comercial, seguimiento de oportunidades y extensión de pruebas.",
                "permissions": [
                    "saas.dashboard.view",
                    "saas.tenants.view",
                    "saas.tenants.extend_trial",
                ],
            },
            {
                "code": "FINANCE",
                "label": "Finanzas SaaS",
                "description": "Consulta de recaudación, planes, facturación y métricas financieras.",
                "permissions": [
                    "saas.dashboard.view",
                    "saas.tenants.view",
                    "saas.finance.view",
                    "saas.metrics.view",
                ],
            },
        ]
