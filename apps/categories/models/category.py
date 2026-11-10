from django.db import models

from apps.core.models.tenant_model import TenantModel


class Category(TenantModel):
    """
    Modelo que representa una categoría de productos
    dentro del sistema inventario-pme aislada por empresa.
    """

    id_category = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Nombre",
        help_text="Nombre de la categoria.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripcion",
        help_text="Descripcion de la categoria.",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Categoria padre",
        help_text="Categoria superior a la que pertenece esta categoria.",
    )

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "Categorias"
        db_table = "categories"
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["company", "is_active"],
                name="category_comp_active_idx",
            ),
            models.Index(
                fields=["name"],
                name="category_name_idx",
            ),
            models.Index(
                fields=["is_active"],
                name="category_active_idx",
            ),
            models.Index(
                fields=["parent"],
                name="category_parent_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "parent", "name"],
                name="category_unique_name_per_parent",
            ),
        ]

    def __str__(self) -> str:
        """
        Devuelve la representacion legible de la categoria.
        """

        return self.name
