import logging
from typing import Any, Iterable, List, Optional, Set, Union

from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError
from django.db.models import Q

logger = logging.getLogger(__name__)
User = get_user_model()


class RecipientResolver:
    """
    Servicio de resolución inteligente de destinatarios para notificaciones.
    Determina qué usuarios deben recibir un evento según:
    - Destinatarios específicos (IDs o instancias de User)
    - Pertenencia a la empresa (CompanyMembership activa)
    - Condición de Propietario (Owner)
    - Permisos específicos o rol funcional
    - Administradores globales de SaaS (is_staff / is_superuser)
    """

    @classmethod
    def resolve_recipients(
        cls,
        company_id: Optional[Union[int, str]] = None,
        permission_code: Optional[str] = None,
        role_name: Optional[str] = None,
        specific_users: Optional[Iterable[Any]] = None,
        is_saas_admin: bool = False,
        include_owners: bool = True,
        exclude_user_ids: Optional[Iterable[int]] = None,
    ) -> List[Any]:
        """
        Calcula y retorna la lista unificada de usuarios destinatarios (sin duplicados).
        """
        recipients_map = {}  # {user_id: user_instance}
        exclude_set: Set[int] = set()

        if exclude_user_ids:
            for item in exclude_user_ids:
                if hasattr(item, "id"):
                    exclude_set.add(item.id)
                elif hasattr(item, "pk"):
                    exclude_set.add(item.pk)
                else:
                    try:
                        exclude_set.add(int(item))
                    except (ValueError, TypeError):
                        pass

        # 1. Si se especifican usuarios directos
        if specific_users:
            for u in specific_users:
                if u is None:
                    continue
                user_obj = None
                if isinstance(u, User):
                    user_obj = u
                elif isinstance(u, (int, str)):
                    try:
                        uid = int(u)
                        user_obj = User.objects.filter(pk=uid, is_active=True).first()
                    except (ValueError, TypeError, ProgrammingError, OperationalError):
                        user_obj = None
                elif hasattr(u, "user") and isinstance(u.user, User):
                    user_obj = u.user

                if user_obj and user_obj.is_active and user_obj.pk not in exclude_set:
                    recipients_map[user_obj.pk] = user_obj

        # 2. Si es para administradores globales de SaaS Admin
        if is_saas_admin:
            try:
                saas_admins = User.objects.filter(
                    Q(is_superuser=True) | Q(is_staff=True),
                    is_active=True,
                )
                for admin in saas_admins:
                    if admin.pk not in exclude_set:
                        recipients_map[admin.pk] = admin
            except (ProgrammingError, OperationalError) as e:
                logger.warning("Error resolviendo SaaS admins: %s", e)

        # 3. Si se especifica una empresa (CompanyMembership)
        if company_id is not None:
            try:
                from apps.users.models.company_membership import CompanyMembership

                c_id = int(company_id)
                memberships = CompanyMembership.objects.filter(
                    company_id=c_id,
                    status=CompanyMembership.MembershipStatus.ACTIVE,
                    user__is_active=True,
                ).select_related("user", "role")

                for m in memberships:
                    u = m.user
                    if not u or u.pk in exclude_set:
                        continue

                    # Si es propietario y se incluyen propietarios
                    if include_owners and m.is_owner:
                        recipients_map[u.pk] = u
                        continue

                    # Filtro por nombre de rol
                    if role_name:
                        if m.role and m.role.role_name.lower() == role_name.lower():
                            recipients_map[u.pk] = u
                            continue
                        elif not permission_code:
                            continue

                    # Filtro por permiso granular en JSONField del rol
                    if permission_code:
                        if m.role and isinstance(m.role.permissions, dict):
                            perms = m.role.permissions
                            # Verificamos permiso directo o comodín '*'
                            if (
                                perms.get(permission_code) is True
                                or perms.get("*") is True
                            ):
                                recipients_map[u.pk] = u
                                continue
                            # Verificamos permiso por módulo (ej. 'inventory.*' para 'inventory.view')
                            module_prefix = permission_code.split(".")[0] + ".*"
                            if perms.get(module_prefix) is True:
                                recipients_map[u.pk] = u
                                continue
                    elif not role_name:
                        # Si no hay restricción de permiso ni rol para la empresa, recibe todos los miembros activos
                        recipients_map[u.pk] = u

            except (ProgrammingError, OperationalError) as e:
                logger.warning(
                    "Error resolviendo miembros de empresa %s: %s", company_id, e
                )
            except Exception as e:
                logger.error(
                    "Error inesperado en RecipientResolver para empresa %s: %s",
                    company_id,
                    e,
                )

        return list(recipients_map.values())
