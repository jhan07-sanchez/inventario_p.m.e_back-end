"""
Servicio especializado en la generación y resolución de canales de contacto,
soporte y renovación para clientes SaaS (WhatsApp y Correo Electrónico).
Sigue el principio de Responsabilidad Única (SRP).
"""

from typing import Optional, Tuple
from urllib.parse import quote

from django.conf import settings


class SubscriptionContactService:
    """
    Servicio de dominio para construir URLs dinámicas de soporte y renovación comercial.
    Lee los valores de configuración de settings.SUPPORT_WHATSAPP y settings.SUPPORT_EMAIL.
    """

    @staticmethod
    def get_channels(company=None) -> Tuple[Optional[str], Optional[str]]:
        """
        Retorna una tupla (contact_whatsapp, contact_email).
        Si la variable de entorno correspondiente no está configurada o está vacía,
        retorna None para ese canal.
        """
        whatsapp_raw = getattr(settings, "SUPPORT_WHATSAPP", "") or ""
        email_raw = getattr(settings, "SUPPORT_EMAIL", "") or ""

        company_name = ""
        if company:
            company_name = (
                getattr(company, "trade_name", None)
                or getattr(company, "business_name", None)
                or ""
            )

        contact_whatsapp = None
        if str(whatsapp_raw).strip():
            clean_number = "".join(filter(str.isdigit, str(whatsapp_raw).strip()))
            if clean_number:
                msg = f"Hola, deseo renovar o activar el plan de mi empresa {company_name or 'mi empresa'} en Inventario PME."
                contact_whatsapp = f"https://wa.me/{clean_number}?text={quote(msg)}"

        contact_email = None
        if str(email_raw).strip():
            subject = f"Renovación de plan - {company_name or 'Empresa'}"
            contact_email = f"mailto:{str(email_raw).strip()}?subject={quote(subject)}"

        return contact_whatsapp, contact_email
