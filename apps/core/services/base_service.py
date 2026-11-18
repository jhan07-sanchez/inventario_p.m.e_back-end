from typing import Any, Generic, Optional, TypeVar

from django.db import models, transaction

# Definimos una variable de tipo que debe ser un Modelo de Django
ModelType = TypeVar("ModelType", bound=models.Model)


class BaseService(Generic[ModelType]):
    """
    Servicio base genérico que encapsula la lógica de negocio y las mutaciones
    de datos (Creación, Actualización, Eliminación).
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    def validate(
        self, data: dict[str, Any], instance: Optional[ModelType] = None
    ) -> dict[str, Any]:
        """
        Hook para aplicar reglas de negocio ANTES de modificar la BD.
        Si la validación falla, se debe levantar una ValidationError.
        """
        return data

    def perform_create(self, data: dict[str, Any]) -> ModelType:
        """Hook opcional para cambiar cómo se instancia/crea un registro en BD."""
        return self.model.objects.create(**data)

    def perform_update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        """Hook opcional para cambiar cómo se actualiza un registro existente."""
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def perform_delete(self, instance: ModelType, soft_delete: bool = True) -> None:
        """Hook opcional para definir el comportamiento exacto al borrar."""
        if soft_delete:
            if hasattr(instance, "soft_delete"):
                instance.soft_delete()
            else:
                instance.delete()
        else:
            if hasattr(instance, "hard_delete"):
                instance.hard_delete()
            else:
                instance.delete()

    def _is_tenant_model(self) -> bool:
        if not self.model:
            return False
        try:
            from apps.core.models.tenant_model import TenantModel

            if issubclass(self.model, TenantModel):
                return True
        except Exception:
            pass
        fields = [f.name for f in getattr(self.model._meta, "fields", [])]
        return "company" in fields or "company_id" in fields

    def validate_cross_tenant_integrity(
        self, data: dict[str, Any], company_id: Any
    ) -> None:
        """
        Verifica que todas las claves foráneas pasadas pertenezcan a la misma empresa.
        Previene la inyección de entidades ajenas (cross-tenant relational injection).
        """
        if not company_id:
            return
        comp_id = (
            getattr(company_id, "id_company", None)
            or getattr(company_id, "pk", None)
            or company_id
        )

        for field_name, value in data.items():
            if value is not None and hasattr(value, "company_id"):
                rel_comp_id = getattr(value, "company_id", None)
                if rel_comp_id is not None and rel_comp_id != comp_id:
                    from django.core.exceptions import ValidationError

                    raise ValidationError(
                        f"La entidad relacionada '{field_name}' pertenece a otra empresa."
                    )

    @transaction.atomic
    def create(self, **data: Any) -> ModelType:
        """
        Flujo central de creación.
        Aplica validaciones -> Construye -> Retorna el objeto.
        Inyecta automáticamente company_id y verifica integridad relacional multi-tenant.
        """
        if self._is_tenant_model():
            from apps.core.context import get_current_company_id

            comp_id = (
                data.get("company_id")
                or getattr(data.get("company"), "pk", None)
                or get_current_company_id()
            )
            if comp_id:
                if "company_id" not in data and "company" not in data:
                    data["company_id"] = comp_id
                self.validate_cross_tenant_integrity(data, comp_id)

        validated_data = self.validate(data)
        return self.perform_create(validated_data)

    @transaction.atomic
    def update(self, instance: ModelType, **data: Any) -> ModelType:
        """
        Flujo central de actualización.
        Aplica validaciones de negocio y luego actualiza.
        Garantiza que la empresa del registro no sea alterada.
        """
        if self._is_tenant_model():
            existing_company_id = getattr(instance, "company_id", None)
            if existing_company_id:
                data["company_id"] = existing_company_id
                self.validate_cross_tenant_integrity(data, existing_company_id)

        validated_data = self.validate(data, instance=instance)
        return self.perform_update(instance, validated_data)

    @transaction.atomic
    def delete(self, instance: ModelType, soft_delete: bool = True) -> None:
        """
        Flujo central de eliminación. Realiza soft-delete por defecto si el modelo
        soporta soft delete.
        """
        self.perform_delete(instance, soft_delete=soft_delete)

    @transaction.atomic
    def restore(self, instance: ModelType) -> ModelType:
        """
        Restaura un registro eliminado si este utilizaba soft delete.
        """
        if hasattr(instance, "restore"):
            instance.restore()
        elif hasattr(instance, "is_active") and not instance.is_active:
            instance.is_active = True
            instance.save(update_fields=["is_active"])
        return instance
