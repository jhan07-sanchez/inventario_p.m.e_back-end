from django.test import TestCase

from apps.core.permissions.base_permission import BaseRolePermission
from apps.core.security.security_data import SECURITY_MODULES
from apps.core.security.registry import SecurityRegistry
from apps.core.security.services.permission_service import PermissionService
from apps.users.models import Role, User, UserRole
from apps.users.permissions import CanReadUsers
from apps.users.services.role_service import RoleService
from apps.users.services.user_service import UserService


class SecurityAuditFixesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sec_user",
            password="secpassword123",
            email="sec@example.com",
            document_number="12398745",
        )
        self.role = Role.objects.create(
            role_name="operator_role",
            permissions={
                "users.view": True,
                "invoices.view": True,
                "invoices.create": True,
            },
        )
        self.user_role = UserRole.objects.create(user=self.user, role=self.role)

    def test_invoices_module_in_security_modules_and_registry(self):
        """
        Verifica que el módulo invoices esté registrado en SECURITY_MODULES
        y que SecurityRegistry y RoleService permitan asignar sus permisos.
        """
        all_codes = SecurityRegistry.get_all_security_codes()
        self.assertIn("invoices.view", all_codes)
        self.assertIn("invoices.create", all_codes)
        self.assertIn("invoices.update", all_codes)
        self.assertIn("invoices.delete", all_codes)

        # RoleService validation must not raise InvalidRolePermissionsException
        RoleService._validate_permissions({
            "invoices.view": True,
            "invoices.create": True,
        })

    def test_legacy_base_role_permission_resolves_without_field_error(self):
        """
        Verifica que BaseRolePermission y subclases legadas (CanReadUsers)
        se evalúen a través de PermissionService sin lanzar FieldError.
        """
        class DummyRequest:
            def __init__(self, user):
                self.user = user

        req = DummyRequest(self.user)

        # CanReadUsers maps users_read -> users.view which is granted
        can_read = CanReadUsers()
        self.assertTrue(can_read.has_permission(req, None))

        # Revoke permission
        self.role.permissions = {"users.view": False}
        self.role.save()
        PermissionService.invalidate_user_cache(self.user.pk)

        self.assertFalse(can_read.has_permission(req, None))

    def test_user_service_safe_role_reassignment(self):
        """
        Verifica que reasignar roles en UserService no cause IntegrityError
        en caso de asignaciones previamente borradas lógicamente.
        """
        new_role = Role.objects.create(
            role_name="new_test_role",
            permissions={"users.view": True},
        )

        service = UserService()
        # First assignment of new_role
        service.perform_update(self.user, {"roles": [new_role.pk]})
        self.assertTrue(
            UserRole.objects.filter(user=self.user, role=new_role).exists()
        )

        # Reassign back to original role (new_role is soft-deleted)
        service.perform_update(self.user, {"roles": [self.role.pk]})
        self.assertFalse(
            UserRole.objects.filter(user=self.user, role=new_role).exists()
        )

        # Reassign again to new_role: must restore softly-deleted assignment without IntegrityError
        service.perform_update(self.user, {"roles": [new_role.pk]})
        self.assertTrue(
            UserRole.objects.filter(user=self.user, role=new_role).exists()
        )
