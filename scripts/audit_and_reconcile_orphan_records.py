"""
Script de auditoría y reconciliación segura de registros huérfanos (company_id IS NULL).
Requisito previo obligatorio antes de aplicar la restricción NOT NULL en PostgreSQL.

Reglas:
1. Identifica y reporta registros sin company_id en todos los modelos multi-tenant.
2. No asigna empresas de forma arbitraria (Regla 5).
3. Intenta deducir la empresa únicamente mediante relaciones deterministas comprobables:
   - Sale -> customer.company_id
   - Purchase -> supplier.company_id
   - Product -> category.company_id
   - CashSession -> cash_register.company_id
4. Registros sin relación determinista se reportan como AMBIGUOS para revisión manual.
5. InvoiceTemplate con company_id=NULL se clasifica como 'Plantilla Global del Sistema' (Legítimo).
6. Por defecto ejecuta en modo DRY-RUN (solo lectura y reporte).
"""

import os
import sys

import django

# Setup django environment if executed directly
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

from django.db import transaction

from apps.cash.models import CashRegister, CashSession
from apps.categories.models import Category
from apps.customers.models import Customer
from apps.invoices.models import Invoice, InvoiceTemplate
from apps.products.models import Product
from apps.purchases.models import Purchase
from apps.sales.models import Sale
from apps.suppliers.models import Supplier

MODELS_TO_AUDIT = [
    ("Customer", Customer, "id_customer", False),
    ("Supplier", Supplier, "id_supplier", False),
    ("Category", Category, "id_category", False),
    ("Product", Product, "id_product", False),
    ("Purchase", Purchase, "id_purchase", False),
    ("Sale", Sale, "id_sale", False),
    ("Invoice", Invoice, "id", False),
    ("InvoiceTemplate", InvoiceTemplate, "id", True),  # True = Legitimately nullable
    ("CashRegister", CashRegister, "id_cash_register", False),
    ("CashSession", CashSession, "id_cash_session", False),
]


def audit_orphan_records(dry_run: bool = True):
    print("=" * 80)
    print("AUDITORÍA DE INTEGRIDAD: REGISTROS CON company_id IS NULL")
    print(
        f"Modo: {'DRY-RUN (Solo lectura)' if dry_run else 'EJECUCIÓN REAL (Reconciliación)'}"
    )
    print("=" * 80)

    total_orphans = 0
    report = {}

    for name, model, pk_field, allow_null in MODELS_TO_AUDIT:
        manager = getattr(model, "all_objects", model.objects)
        orphans_qs = manager.filter(company__isnull=True)
        count = orphans_qs.count()
        total_orphans += count if not allow_null else 0
        report[name] = {
            "count": count,
            "allow_null": allow_null,
            "sample_ids": list(orphans_qs.values_list(pk_field, flat=True)[:10]),
        }

        tag = (
            "[PERMITIDO - GLOBAL]"
            if allow_null
            else ("[ALERTA - HUÉRFANO]" if count > 0 else "[OK - LIMPIO]")
        )
        print(f"{tag:<25} {name:<18}: {count:>5} registros con company_id IS NULL")
        if count > 0 and not allow_null:
            print(f"    IDs muestra: {report[name]['sample_ids']}")

    print("-" * 80)
    print(
        f"Total de registros de negocio huérfanos que bloquean la migración NOT NULL: {total_orphans}"
    )
    print("=" * 80)

    if total_orphans == 0:
        print(
            "✅ La base de datos está completamente lista para aplicar NOT NULL a company_id."
        )
        return report

    if dry_run:
        print(
            "\nPara reconciliar los registros deterministas en base de datos, ejecute:"
        )
        print("python scripts/audit_and_reconcile_orphan_records.py --apply")
        return report

    print("\nIniciando proceso de reconciliación determinista...")
    reconciled_count = 0
    ambiguous_count = 0

    with transaction.atomic():
        # 1. Reconciliar Products via Category
        for p in Product.all_objects.filter(company__isnull=True):
            if p.category and p.category.company_id:
                p.company_id = p.category.company_id
                p.save(update_fields=["company"])
                reconciled_count += 1
            else:
                ambiguous_count += 1

        # 2. Reconciliar Sales via Customer
        for s in Sale.all_objects.filter(company__isnull=True):
            if s.customer and s.customer.company_id:
                s.company_id = s.customer.company_id
                s.save(update_fields=["company"])
                reconciled_count += 1
            else:
                ambiguous_count += 1

        # 3. Reconciliar Purchases via Supplier
        for pur in Purchase.all_objects.filter(company__isnull=True):
            if pur.supplier and pur.supplier.company_id:
                pur.company_id = pur.supplier.company_id
                pur.save(update_fields=["company"])
                reconciled_count += 1
            else:
                ambiguous_count += 1

        # 4. Reconciliar CashSessions via CashRegister
        for cs in CashSession.all_objects.filter(company__isnull=True):
            if cs.cash_register and cs.cash_register.company_id:
                cs.company_id = cs.cash_register.company_id
                cs.save(update_fields=["company"])
                reconciled_count += 1
            else:
                ambiguous_count += 1

    print(f"Reconciliados determinísticamente: {reconciled_count}")
    print(
        f"Registros ambiguos restantes (requieren revisión manual de negocio): {ambiguous_count}"
    )
    return report


if __name__ == "__main__":
    apply_mode = "--apply" in sys.argv
    audit_orphan_records(dry_run=not apply_mode)
