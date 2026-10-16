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

    @transaction.atomic
    def create(self, **data: Any) -> ModelType:
        """
        Flujo central de creación.
        Aplica validaciones -> Construye -> Retorna el objeto.
        """
        validated_data = self.validate(data)
        return self.perform_create(validated_data)

    @transaction.atomic
    def update(self, instance: ModelType, **data: Any) -> ModelType:
        """
        Flujo central de actualización.
        Aplica validaciones de negocio y luego actualiza.
        """
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
