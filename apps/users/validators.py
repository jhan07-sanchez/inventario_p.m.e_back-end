from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _




document_number_validator = RegexValidator(
    regex=r"^[0-9]+$", message="El número de documento solo puede contener numeros."
)



class DynamicPasswordLengthValidator:
    """
    Validador de contraseña que lee la longitud minima desde los Parametros Globales.
    """

    def validate(self, password, user=None):
        from apps.configuration.services.global_parameter_service import (
            GlobalParameterService,
        )
        # Consultamos el parametro (gracias al cache, es casi instantaneo)
        min_length = GlobalParameterService.get_typed_value(
            "SECURITY_PASSWORD_MIN_LENGTH", default=8
        )

        if len(password) < min_length:
            raise ValidationError(
                _("La contraseña debe tener al menos %(min_length)d caracteres."),
                code="password_too_short",
                params={"min_length": min_length},
            )

    def get_help_text(self):
        from apps.configuration.services.global_parameter_service import (
            GlobalParameterService,
        )
        min_length = GlobalParameterService.get_typed_value(
            "SECURITY_PASSWORD_MIN_LENGTH", default=8
        )
        return _("Su contraseña debe contener al menos %(min_length)d caracteres.") % {
            "min_length": min_length
        }
