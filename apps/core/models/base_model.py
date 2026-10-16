from django.db import models
from django.utils import timezone


class BaseManager(models.Manager):
    """
    Manager base que filtra los registros eliminados lógicamente.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """
    Modelo base para todas las entidades del sistema.

    Contiene únicamente los campos comunes que serán
    heredados por los demás modelos. Incluye Soft Delete.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualización",
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de eliminación",
    )

    objects = BaseManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Sobrescribe el método delete para realizar un borrado lógico (Soft Delete).
        Sincroniza deleted_at e is_active (si el modelo lo soporta).
        """
        self.deleted_at = timezone.now()
        fields = ["deleted_at"]
        if hasattr(self, "is_active"):
            self.is_active = False
            fields.append("is_active")
        if hasattr(self, "updated_at"):
            fields.append("updated_at")
        self.save(update_fields=fields)

    def hard_delete(self, using=None, keep_parents=False):
        """
        Realiza una eliminación física definitiva del registro en la base de datos.
        """
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """
        Restaura un registro eliminado lógicamente.
        Sincroniza deleted_at e is_active (si el modelo lo soporta).
        """
        self.deleted_at = None
        fields = ["deleted_at"]
        if hasattr(self, "is_active"):
            self.is_active = True
            fields.append("is_active")
        if hasattr(self, "updated_at"):
            fields.append("updated_at")
        self.save(update_fields=fields)
