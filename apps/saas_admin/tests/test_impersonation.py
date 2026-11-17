from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.company_info.models import CompanyInfo
from apps.core.exceptions import (
    CannotImpersonateSuperuserException,
    ChainedImpersonationDeniedException,
    TargetUserNotInTenantException,
    TenantNotFoundException,
)
from apps.core.models.audit_log import AuditLog
from apps.saas_admin.dto.impersonation_dto import ImpersonationRequestDTO
from apps.saas_admin.services.impersonation_service import ImpersonationService
from apps.users.models import CompanyMembership, Role

User = get_user_model()


class TestImpersonationService(TestCase):
    """
    Pruebas de alta seguridad para el servicio de impersonación temporal de soporte.
    """

    def setUp(self):
        cache.clear()

        # 1. Superadministrador
        self.superadmin = User.objects.create_superuser(
            username="super_saas",
            email="admin@saas.com",
            password="Password123!",
            document_number="99000030",
        )

        # 2. Otro Superadministrador (objetivo prohibido)
        self.another_superadmin = User.objects.create_superuser(
            username="another_super",
            email="another@saas.com",
            password="Password123!",
            document_number="99000031",
        )

        # 3. Usuario regular no admin
        self.non_admin = User.objects.create_user(
            username="regular_joe",
            email="joe@test.com",
            password="Password123!",
            document_number="99000032",
        )

        # 4. Tenant y propietario
        self.tenant_owner = User.objects.create_user(
            username="owner_user",
            email="owner@tenant.com",
            password="Password123!",
            document_number="99000033",
            first_name="Carlos",
            last_name="Gomez",
        )
        self.company = CompanyInfo.objects.create(
            business_name="Cliente Soporte SAS",
            tax_id="900888999-1",
            owner_user=self.tenant_owner,
        )
        self.role_owner = Role.objects.create(
            role_name="Admin",
            is_active=True,
        )
        self.membership_owner = CompanyMembership.objects.create(
            user=self.tenant_owner,
            company=self.company,
            role=self.role_owner,
            is_owner=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        # 5. Colaborador dentro del mismo tenant
        self.employee = User.objects.create_user(
            username="employee_user",
            email="employee@tenant.com",
            password="Password123!",
            document_number="99000034",
        )
        self.role_employee = Role.objects.create(
            role_name="Vendedor",
            is_active=True,
        )
        self.membership_employee = CompanyMembership.objects.create(
            user=self.employee,
            company=self.company,
            role=self.role_employee,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        # 6. Usuario de otra empresa ajena
        self.outsider = User.objects.create_user(
            username="outsider_user",
            email="outsider@other.com",
            password="Password123!",
            document_number="99000035",
        )

    def test_impersonation_success_default_owner(self):
        """Superadministrador inicia sesión temporal resolviendo por defecto al dueño de la empresa."""
        dto = ImpersonationRequestDTO(
            company_id=self.company.id_company,
            reason="Diagnóstico de error en facturación electrónica",
        )

        result = ImpersonationService.start_impersonation(
            admin_user=self.superadmin,
            dto=dto,
        )

        self.assertIsNotNone(result.access_token)
        self.assertEqual(result.token_type, "Bearer")
        self.assertEqual(result.expires_in, 900)  # 15 minutos
        self.assertEqual(result.target_user["id_user"], self.tenant_owner.id_user)
        self.assertEqual(result.target_company["id_company"], self.company.id_company)
        self.assertEqual(result.impersonated_by["id_user"], self.superadmin.id_user)

        # Validar claims criptográficos dentro del token
        token_obj = AccessToken(result.access_token)
        self.assertTrue(token_obj.get("is_impersonated"))
        self.assertEqual(token_obj.get("impersonator_id"), self.superadmin.id_user)
        self.assertEqual(token_obj.get("impersonator_email"), self.superadmin.email)
        self.assertEqual(token_obj.get("company_id"), self.company.id_company)
        self.assertEqual(token_obj.get("impersonated_company"), self.company.id_company)
        self.assertEqual(token_obj.get("impersonation_reason"), dto.reason)

        # Validar registro en AuditLog
        log = AuditLog.objects.filter(company=self.company).first()
        self.assertIsNotNone(log)
        self.assertEqual(
            log.payload.get("security_event"), "SUPPORT_IMPERSONATION_STARTED"
        )
        self.assertEqual(log.payload.get("target_user_id"), self.tenant_owner.id_user)

    def test_impersonation_success_specific_employee(self):
        """Superadministrador inicia sesión temporal especificando un colaborador de la empresa."""
        dto = ImpersonationRequestDTO(
            company_id=self.company.id_company,
            target_user_id=self.employee.id_user,
            reason="Prueba de permisos del cajero",
        )

        result = ImpersonationService.start_impersonation(
            admin_user=self.superadmin,
            dto=dto,
        )

        self.assertEqual(result.target_user["id_user"], self.employee.id_user)

    def test_non_superuser_actor_denied(self):
        """Un usuario que no sea superadministrador no puede iniciar impersonación."""
        dto = ImpersonationRequestDTO(
            company_id=self.company.id_company,
            reason="Intento no autorizado",
        )

        with self.assertRaises(PermissionDenied):
            ImpersonationService.start_impersonation(
                admin_user=self.non_admin,
                dto=dto,
            )

    def test_cannot_impersonate_another_superuser(self):
        """Está estrictamente prohibido impersonar a otro Superadministrador."""
        # Supongamos que otro superadmin tiene membresía en la empresa
        CompanyMembership.objects.create(
            user=self.another_superadmin,
            company=self.company,
            role=self.role_owner,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )

        dto = ImpersonationRequestDTO(
            company_id=self.company.id_company,
            target_user_id=self.another_superadmin.id_user,
            reason="Intento de escalar privilegios",
        )

        with self.assertRaises(CannotImpersonateSuperuserException):
            ImpersonationService.start_impersonation(
                admin_user=self.superadmin,
                dto=dto,
            )

    def test_target_user_not_in_tenant_denied(self):
        """No se puede impersonar a un usuario que no pertenezca a la empresa."""
        dto = ImpersonationRequestDTO(
            company_id=self.company.id_company,
            target_user_id=self.outsider.id_user,
            reason="Acceso a usuario ajeno",
        )

        with self.assertRaises(TargetUserNotInTenantException):
            ImpersonationService.start_impersonation(
                admin_user=self.superadmin,
                dto=dto,
            )

    def test_chained_impersonation_denied(self):
        """Prohibido iniciar una impersonación si la sesión actual ya es una sesión impersonada."""
        dto = ImpersonationRequestDTO(
            company_id=self.company.id_company,
            reason="Intento encadenado",
        )

        with self.assertRaises(ChainedImpersonationDeniedException):
            ImpersonationService.start_impersonation(
                admin_user=self.superadmin,
                dto=dto,
                is_already_impersonated=True,
            )

    def test_nonexistent_company_denied(self):
        """Empresa inexistente lanza TenantNotFoundException."""
        dto = ImpersonationRequestDTO(
            company_id=999999,
            reason="Empresa fantasma",
        )

        with self.assertRaises(TenantNotFoundException):
            ImpersonationService.start_impersonation(
                admin_user=self.superadmin,
                dto=dto,
            )
