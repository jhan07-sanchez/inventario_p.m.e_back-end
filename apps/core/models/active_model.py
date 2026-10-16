from django.db import models

from .base_model import BaseModel


class ActiveModel(BaseModel):
    """
    Modelo abstracto que añade soporte para registros activos e inactivos.

    Todas las entidades del sistema que requieran borrado lógico
    deben heredar de esta clase.

    Funcionalidades:
        - Campo is_active.
        - Borrado lógico (soft_delete).
        - Restauración de registros (restore).
    """

    is_active = models.BooleanField(
        default=True,
        verbose_name="Estado",
        help_text="Indica si el registro se encuentra activo.",
        db_index=True,
    )

    class Meta:
        abstract = True

    def soft_delete(self, save: bool = True) -> None:
        """
        Realiza un borrado lógico del registro sincronizando is_active y deleted_at.

        Args:
            save (bool):
                Si es True, guarda inmediatamente los cambios.
        """
        from django.utils import timezone

        self.is_active = False
        self.deleted_at = timezone.now()

        if save:
            self.save(
                update_fields=[
                    "is_active",
                    "deleted_at",
                    "updated_at",
                ]
            )

    def restore(self, save: bool = True) -> None:
        """
        Restaura un registro previamente desactivado sincronizando is_active y deleted_at.

        Args:
            save (bool):
                Si es True, guarda inmediatamente los cambios.
        """
        self.is_active = True
        self.deleted_at = None

        if save:
            self.save(
                update_fields=[
                    "is_active",
                    "deleted_at",
                    "updated_at",
                ]
            )

    @property
    def is_enabled(self) -> bool:
        """
        Indica si el registro se encuentra activo.
        """

        return self.is_active
