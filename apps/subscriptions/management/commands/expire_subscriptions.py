import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models.audit_log import AuditLog
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Comando para procesar automáticamente la expiración de suscripciones SaaS
    y aplicar las transiciones de estado de acuerdo a las reglas de negocio:

    1. TRIAL:
       - Vencida (now > end_date): Transición directa a EXPIRED (sin período de gracia).
    2. ACTIVE:
       - Vencida dentro de gracia (now > end_date y now <= end_date + grace_days): Transición a PAST_DUE.
       - Vencida fuera de gracia (now > end_date + grace_days): Transición directa a EXPIRED.
    3. PAST_DUE:
       - Vencida fuera de gracia (now > end_date + grace_days): Transición a EXPIRED.

    El comando es idempotente, registra auditoría en AuditLog, maneja excepciones por suscripción
    y soporta ejecución simulada con --dry-run.
    """

    help = "Evalúa y aplica la expiración automática de suscripciones según su ciclo de vida y período de gracia."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la ejecución del comando sin persistir cambios en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "--- [MODO DRY-RUN ACTIVADO]: No se guardarán cambios en la BD ---"
                )
            )

        self.stdout.write(
            f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando proceso de expiración de suscripciones..."
        )

        # Consultar suscripciones potencialmente afectables (TRIAL, ACTIVE, PAST_DUE activas)
        candidates = (
            Subscription.objects.filter(
                is_active=True,
                status__in=[
                    Subscription.Status.TRIAL,
                    Subscription.Status.ACTIVE,
                    Subscription.Status.PAST_DUE,
                ],
            )
            .select_related("company", "plan")
            .order_by("id_subscription")
        )

        total_candidates = candidates.count()
        processed_count = 0
        expired_count = 0
        grace_period_count = 0
        errors_count = 0

        for sub in candidates:
            processed_count += 1
            old_status = sub.status
            target_status = None
            reason = ""

            try:
                # Regla 1: TRIAL
                if old_status == Subscription.Status.TRIAL:
                    if now > sub.end_date:
                        target_status = Subscription.Status.EXPIRED
                        reason = (
                            f"Período de prueba (TRIAL) finalizado el {sub.end_date.strftime('%Y-%m-%d %H:%M:%S')}. "
                            "No aplica período de gracia."
                        )

                # Regla 2: ACTIVE
                elif old_status == Subscription.Status.ACTIVE:
                    if now > sub.end_date:
                        grace_days = sub.grace_period_days or 0
                        grace_deadline = sub.end_date + timedelta(days=grace_days)
                        if grace_days > 0 and now <= grace_deadline:
                            target_status = Subscription.Status.PAST_DUE
                            reason = (
                                f"Suscripción ACTIVE vencida el {sub.end_date.strftime('%Y-%m-%d %H:%M:%S')}. "
                                f"Entrando a período de gracia hasta {grace_deadline.strftime('%Y-%m-%d %H:%M:%S')}."
                            )
                            grace_period_count += 1
                        else:
                            target_status = Subscription.Status.EXPIRED
                            reason = (
                                f"Suscripción ACTIVE vencida el {sub.end_date.strftime('%Y-%m-%d %H:%M:%S')}. "
                                "Período de gracia agotado o no configurado."
                            )

                # Regla 3: PAST_DUE
                elif old_status == Subscription.Status.PAST_DUE:
                    grace_days = sub.grace_period_days or 0
                    grace_deadline = sub.end_date + timedelta(days=grace_days)
                    if now > grace_deadline:
                        target_status = Subscription.Status.EXPIRED
                        reason = (
                            f"Período de gracia de PAST_DUE finalizado el {grace_deadline.strftime('%Y-%m-%d %H:%M:%S')}."
                        )
                    else:
                        # Permanece en gracia
                        grace_period_count += 1

                # Si no requiere cambio de estado, continuar
                if not target_status or target_status == old_status:
                    continue

                if target_status == Subscription.Status.EXPIRED:
                    expired_count += 1

                if not dry_run:
                    with transaction.atomic():
                        # Bloqueo a nivel de fila (select_for_update con skip_locked) para proteger ante ejecuciones simultáneas
                        locked_sub = (
                            Subscription.objects.select_for_update(skip_locked=True)
                            .filter(pk=sub.pk)
                            .first()
                        )
                        if not locked_sub:
                            logger.info(
                                f"[expire_subscriptions] Suscripción #{sub.pk} omitida: bloqueada por otra ejecución concurrente."
                            )
                            continue

                        # Si el estado fue cambiado por otro proceso concurrente, omitir
                        if locked_sub.status != old_status:
                            continue

                        locked_sub.status = target_status
                        locked_sub.notes = (
                            f"{locked_sub.notes}\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] "
                            f"Transición automática: {old_status} -> {target_status}. {reason}"
                        ).strip()
                        locked_sub.save(update_fields=["status", "notes", "updated_at"])

                        # Registrar en AuditLog
                        AuditLog.objects.create(
                            user=None,
                            company=locked_sub.company,
                            method="SYSTEM",
                            path="management/expire_subscriptions",
                            ip_address="127.0.0.1",
                            user_agent="Django Management Command / Cron",
                            status_code=200,
                            payload={
                                "action": "AUTO_SUBSCRIPTION_TRANSITION",
                                "subscription_id": locked_sub.pk,
                                "company_id": locked_sub.company_id,
                                "company_name": str(locked_sub.company),
                                "plan_code": locked_sub.plan.code if locked_sub.plan else None,
                                "previous_status": old_status,
                                "new_status": target_status,
                                "reason": reason,
                                "end_date": locked_sub.end_date.isoformat(),
                                "timestamp": now.isoformat(),
                            },
                        )

                        # Invalidar caché multi-tenant de suscripción y permisos tras confirmar la transacción
                        comp_id = locked_sub.company_id
                        transaction.on_commit(
                            lambda c_id=comp_id: SubscriptionService.invalidate_subscription_cache(
                                c_id
                            )
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [ID #{sub.pk}] Empresa: {sub.company} | Plan: {sub.plan.code} | "
                        f"Transición: {old_status} -> {target_status} | {reason}"
                    )
                )

            except Exception as e:
                errors_count += 1
                logger.error(
                    f"[expire_subscriptions] Error procesando suscripción #{sub.pk}: {e!s}",
                    exc_info=True,
                )
                self.stdout.write(
                    self.style.ERROR(
                        f"  [ERROR] Falla al procesar suscripción #{sub.pk}: {e!s}"
                    )
                )

        # Resumen consolidado
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.MIGRATE_HEADING("RESUMEN DE EJECUCIÓN:"))
        self.stdout.write(f"  - Candidatos encontrados: {total_candidates}")
        self.stdout.write(f"  - Suscripciones procesadas: {processed_count}")
        self.stdout.write(
            self.style.SUCCESS(f"  - Suscripciones expiradas: {expired_count}")
        )
        self.stdout.write(
            self.style.WARNING(
                f"  - Suscripciones en período de gracia: {grace_period_count}"
            )
        )
        if errors_count > 0:
            self.stdout.write(
                self.style.ERROR(f"  - Errores encontrados: {errors_count}")
            )
        else:
            self.stdout.write(self.style.SUCCESS("  - Errores encontrados: 0"))
        self.stdout.write("=" * 60)
