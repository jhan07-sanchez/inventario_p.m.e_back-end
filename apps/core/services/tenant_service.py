from typing import Any, Generic, Optional, TypeVar

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.core.services.base_service import BaseService

ModelType = TypeVar("ModelType", bound=models.Model)


class TenantService(BaseService[ModelType], Generic[ModelType]):
    """
    Servicio base multi-tenant.
    Encapsula mutaciones de datos garantizando que:
    1. Ningún registro se cree sin su empresa asociada.
    2. Las entidades relacionadas pertenezcan estrictamente a la misma empresa (Integridad Relacional).
    """

    def validate_cross_tenant_integrity(
        self, data: dict[str, Any], company: Any
    ) -> None:
        """
        Verifica que todas las claves foráneas pasadas pertenezcan a la misma empresa.
        Previene la inyección de entidades ajenas (cross-tenant relational injection).
        """
        comp_id = getattr(company, "id_company", None) or getattr(company, "pk", None) or company

        for field_name, value in data.items():
            if value is not None and hasattr(value, "company_id"):
                if value.company_id != comp_id:
                    raise ValidationError(
                        f"La entidad relacionada '{field_name}' pertenece a otra empresa."
                    )

    @transaction.atomic
    def create_for_company(
        self, company: Any, **data: Any
    ) -> ModelType:
        """
        Flujo central de creación vinculada a una empresa.
        Asigna la empresa y valida integridad multi-tenant antes de persistir.
        """
        if company is None:
            raise ValidationError("Se requiere especificar una empresa válida.")

        data["company"] = company
        self.validate_cross_tenant_integrity(data, company)
        validated_data = self.validate(data)
        return self.perform_create(validated_data)

    @transaction.atomic
    def update_for_company(
        self, instance: ModelType, company: Any, **data: Any
    ) -> ModelType:
        """
        Flujo central de actualización asegurando pertenencia a la empresa.
        """
        comp_id = getattr(company, "id_company", None) or getattr(company, "pk", None) or company
        if hasattr(instance, "company_id") and instance.company_id != comp_id:
            raise ValidationError("No tiene autorización para modificar registros de otra empresa.")

        self.validate_cross_tenant_integrity(data, company)
        validated_data = self.validate(data, instance=instance)
        return self.perform_update(instance, validated_data)

    @transaction.atomic
    def delete_for_company(
        self, instance: ModelType, company: Any, soft_delete: bool = True
    ) -> None:
        """
        Elimina un registro validando que pertenezca a la empresa.
        """
        comp_id = getattr(company, "id_company", None) or getattr(company, "pk", None) or company
        if hasattr(instance, "company_id") and instance.company_id != comp_id:
            raise ValidationError("No tiene autorización para eliminar registros de otra empresa.")

        self.perform_delete(instance, soft_delete=soft_delete)

