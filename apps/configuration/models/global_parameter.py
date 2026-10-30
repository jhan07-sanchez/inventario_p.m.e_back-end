from django.db import models

from apps.core.models.active_model import ActiveModel


class GlobalParameter(ActiveModel):
    """
    Modelo para parámetros configurables del sistema (ej. IVA, moneda, etc.).
    Utilizado para configuraciones dinámicas que no deben estar hardcodeadas.
    """

    class DataType(models.TextChoices):
        STRING = "STRING", "Cadena de texto"
        INTEGER = "INTEGER", "Número entero"
        DECIMAL = "DECIMAL", "Número decimal"
        BOOLEAN = "BOOLEAN", "Booleano"

    id_parameter = models.BigAutoField(primary_key=True, verbose_name="ID")
    key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Clave",
        help_text="Identificador unico del parametro (ej. DEFAULT_TAX_RATE).",
    )
    value = models.TextField(
        verbose_name="Valor",
        help_text="Valor del parametro, puede ser de cualquier tipo (string, int, decimal, boolean).",
    )
    data_type = models.CharField(
        max_length=20,
        choices=DataType.choices,
        default=DataType.STRING,
        verbose_name="Tipo de dato",
        help_text="Tipo de dato del valor del parametro.",
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción",
        help_text="Descripción del parametro, para que sirve y como se utiliza.",
    )

    class Meta:
        db_table = "global_parameters"
        verbose_name = "Parámetro Global"
        verbose_name_plural = "Parámetros Globales"
        ordering = ["key"]

        indexes = [
            models.Index(fields=["key"], name="idx_global_param_key"),
            models.Index(fields=["is_active"], name="idx_global_param_is_active"),
        ]

    def clean(self) -> None:
        """
        Valida que el valor sea compatible con el tipo de dato y normaliza la clave.
        """
        super().clean()
        if self.key:
            self.key = self.key.strip().upper()
        if self.value is not None and self.data_type:
            from apps.configuration.services.global_parameter_service import (
                GlobalParameterService,
            )

            GlobalParameterService.validate_value_by_data_type(
                self.value, self.data_type
            )

    def __str__(self) -> str:
        """Retorna una representación legible del parámetro."""
        return f"{self.key} = {self.value}"
