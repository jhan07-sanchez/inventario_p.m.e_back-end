"""
Señales reactivas del ciclo de vida de suscripciones.
Garantiza la invalidación automática de la caché multi-tenant cuando una
suscripción es modificada o eliminada desde cualquier punto del sistema,
incluyendo el panel de administración de Django (Django Admin).
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.subscriptions.models import Subscription
from apps.subscriptions.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


@receiver(
    post_save,
    sender=Subscription,
    dispatch_uid="subscription_post_save_invalidate_cache",
)
def invalidate_subscription_cache_on_save(sender, instance, **kwargs):
    """
    Invalida reactivamente la caché de suscripción y entitlements tras
    guardar una suscripción en base de datos.
    Se ejecuta tras confirmar la transacción (on_commit) para evitar
    lecturas de caché obsoleta con datos no comprometidos.
    """
    company_id = getattr(instance, "company_id", None)
    if company_id:
        transaction.on_commit(
            lambda: SubscriptionService.invalidate_subscription_cache(company_id)
        )
        logger.debug(
            f"[SubscriptionSignals] Caché programada para invalidación (post_save) en empresa #{company_id}."
        )


@receiver(
    post_delete,
    sender=Subscription,
    dispatch_uid="subscription_post_delete_invalidate_cache",
)
def invalidate_subscription_cache_on_delete(sender, instance, **kwargs):
    """
    Invalida reactivamente la caché tras eliminar una suscripción.
    """
    company_id = getattr(instance, "company_id", None)
    if company_id:
        transaction.on_commit(
            lambda: SubscriptionService.invalidate_subscription_cache(company_id)
        )
        logger.debug(
            f"[SubscriptionSignals] Caché programada para invalidación (post_delete) en empresa #{company_id}."
        )
