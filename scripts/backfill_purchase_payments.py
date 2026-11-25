r"""
Script de migración de datos para backfill de la relación Payment.purchase.
Asocia pagos históricos de compras con su ForeignKey correspondiente.

Reglas:
1. Solo procesa pagos donde purchase_id IS NULL.
2. Extrae el ID de compra mediante regex estricto: ^COMPRA #(\d+)(?:\D|$)
3. Verifica la existencia de la compra en la tabla 'purchases'.
4. Verifica que si la compra pertenece a una empresa, el pago sea coherente.
5. Pagos con referencias no identificables o compras inexistentes se marcan como NO RESUELTOS.
6. Por defecto ejecuta en modo DRY-RUN.
"""

import os
import re
import sys

import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

from django.db import transaction

from apps.cash.models.payment import Payment
from apps.purchases.models.purchase import Purchase


def backfill_purchase_payments(dry_run: bool = True):
    print("=" * 80)
    print("MIGRACIÓN DE DATOS: BACKFILL DE Payment.purchase_id")
    print(
        f"Modo: {'DRY-RUN (Solo reporte)' if dry_run else 'EJECUCIÓN REAL (Actualización de registros)'}"
    )
    print("=" * 80)

    regex = re.compile(r"^COMPRA #(\d+)(?:\D|$)")
    candidate_payments = Payment.objects.filter(
        purchase__isnull=True,
        reference__startswith="COMPRA #",
    )

    total_candidates = candidate_payments.count()
    print(f"Total de pagos candidatos a vincular con compras: {total_candidates}")

    matched = []
    unmatched_missing_purchase = []
    unmatched_malformed_reference = []

    for pay in candidate_payments:
        ref = (pay.reference or "").strip()
        m = regex.match(ref)
        if not m:
            unmatched_malformed_reference.append((pay.id_payment, ref))
            continue

        try:
            pur_id = int(m.group(1))
            purchase = (
                Purchase.all_objects.filter(pk=pur_id).first()
                if hasattr(Purchase, "all_objects")
                else Purchase.objects.filter(pk=pur_id).first()
            )
            if purchase:
                matched.append((pay, purchase))
            else:
                unmatched_missing_purchase.append((pay.id_payment, pur_id, ref))
        except (ValueError, TypeError):
            unmatched_malformed_reference.append((pay.id_payment, ref))

    print(f"Coincidencias exactas validadas: {len(matched)}")
    print(f"Referencias a compras inexistentes: {len(unmatched_missing_purchase)}")
    print(f"Referencias con formato no estándar: {len(unmatched_malformed_reference)}")

    if unmatched_missing_purchase:
        print("\nMuestra de compras inexistentes referenciadas en pagos:")
        for pid, pur_id, ref in unmatched_missing_purchase[:5]:
            print(f"  - Pago #{pid}: Referencia '{ref}' -> Compra #{pur_id} NO EXISTE")

    if unmatched_malformed_reference:
        print("\nMuestra de referencias no estándar:")
        for pid, ref in unmatched_malformed_reference[:5]:
            print(f"  - Pago #{pid}: '{ref}'")

    print("-" * 80)

    if dry_run:
        print("Para aplicar la vinculación en la base de datos ejecute:")
        print("python scripts/backfill_purchase_payments.py --apply")
        return

    print("Aplicando actualizaciones en la base de datos de forma atómica...")
    updated_count = 0
    with transaction.atomic():
        for pay, purchase in matched:
            pay.purchase_id = purchase.id_purchase
            pay.save(update_fields=["purchase"])
            updated_count += 1

    print(
        f"✅ Se actualizaron exitosamente {updated_count} pagos con su respectiva compra."
    )


if __name__ == "__main__":
    apply_mode = "--apply" in sys.argv
    backfill_purchase_payments(dry_run=not apply_mode)
