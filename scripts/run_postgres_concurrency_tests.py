"""
Runner de Pruebas de Concurrencia Real en PostgreSQL — P.M.E.
Ejecuta la suite de concurrencia directamente contra una base de datos PostgreSQL
(Supabase / Staging / Local PostgreSQL) para validar el comportamiento de:
- Row-Level Locking (SELECT ... FOR UPDATE).
- Transacciones concurrentes e integridad multi-hilo.
- Ausencia de deadlocks, sobreventas y sobrepagos.
- Generación de consecutivos empresariales libres de colisiones.

Uso:
    python scripts/run_postgres_concurrency_tests.py [--verbose] [--settings=config.settings.production]
"""

import os
import sys
import time

# Asegurar settings de Django
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    # Si existe TEST_SETTINGS o se pasó por argumento, usarlo; de lo contrario production
    settings_mod = "config.settings.production"
    for arg in sys.argv:
        if arg.startswith("--settings="):
            settings_mod = arg.split("=", 1)[1]
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_mod)

import django

django.setup()

import threading
from decimal import Decimal
from typing import List

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.categories.models import Category
from apps.company_info.models import CompanyInfo
from apps.core.models.company_sequence import CompanySequence
from apps.core.services.company_sequence_service import CompanySequenceService
from apps.inventory.models import Inventory
from apps.inventory.services.inventory_service import InventoryService
from apps.products.models import Product
from apps.users.models import CompanyMembership, Role

User = get_user_model()


def verify_database_engine():
    vendor = connection.vendor
    print("=" * 80)
    print("VERIFICACIÓN DE ENTORNO DE BASE DE DATOS")
    print(f"Motor detectado: {vendor.upper()}")
    print("=" * 80)

    if vendor != "postgresql":
        print("⚠️  ADVERTENCIA:")
        print(
            f"Este runner está diseñado para PostgreSQL. El motor actual es '{vendor}'."
        )
        print("En SQLite, las operaciones multi-hilo concurrentes pueden generar")
        print("'database table is locked' porque SQLite bloquea el archivo completo.")
        if "--force" not in sys.argv:
            print("\nPara ejecutar forzadamente en SQLite agregue el flag --force.")
            print(
                "Para ejecutar en PostgreSQL, configure DATABASE_URL a una base de datos PostgreSQL."
            )
            sys.exit(1)
        else:
            print(
                "Flag --force detectado. Continuando bajo riesgo de bloqueo de tabla..."
            )


def run_scenario_a(company_id: int, num_threads: int = 10):
    """Escenario A: Consecutivos concurrentes sin duplicados."""
    print(
        "\n[ESCENARIO A] Solicitud concurrente de números de venta (select_for_update)"
    )
    print(f"  - Empresa ID: {company_id}")
    print(f"  - Hilos concurrentes: {num_threads}")

    barrier = threading.Barrier(num_threads)
    results: List[str] = []
    errors: List[Exception] = []
    latencies: List[float] = []
    lock = threading.Lock()

    def worker():
        connection.close()
        try:
            barrier.wait()
            t0 = time.perf_counter()
            _, assigned = CompanySequenceService.get_next_number(
                company_id=company_id,
                document_type=CompanySequence.DocumentType.SALE,
                prefix="VTA",
                padding=6,
            )
            elapsed = time.perf_counter() - t0
            with lock:
                results.append(assigned)
                latencies.append(elapsed)
        except Exception as e:
            with lock:
                errors.append(e)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    t_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = time.perf_counter() - t_start

    print(f"  - Tiempo total: {total_time:.4f}s")
    if latencies:
        print(f"  - Latencia promedio por hilo: {sum(latencies) / len(latencies):.4f}s")
        print(f"  - Latencia máx: {max(latencies):.4f}s | mín: {min(latencies):.4f}s")
    print(f"  - Generaciones exitosas: {len(results)}/{num_threads}")
    print(f"  - Números únicos: {len(set(results))}")
    print(f"  - Errores: {len(errors)}")

    if errors:
        for err in errors[:3]:
            print(f"    * Error: {err}")
        return False

    is_ok = len(results) == num_threads and len(set(results)) == num_threads
    status = "✅ EXITOSO (Sin colisiones)" if is_ok else "❌ FALLIDO"
    print(f"  Resultado: {status}")
    return is_ok


def run_scenario_b(inventory_id: int, user, num_threads: int = 4):
    """Escenario B: Salida concurrente de existencias sin sobreventa."""
    print("\n[ESCENARIO B] Descuento simultáneo de stock sin sobreventa")
    inv = Inventory.objects.get(pk=inventory_id)
    initial_stock = inv.current_stock
    # Intentaremos retirar 4 veces x 4.00 = 16.00 cuando el stock es 10.00
    qty_per_thread = Decimal("4.00")
    print(f"  - Stock inicial: {initial_stock}")
    print(
        f"  - Hilos: {num_threads} retirando {qty_per_thread} cada uno (Demanda: {qty_per_thread * num_threads})"
    )

    barrier = threading.Barrier(num_threads)
    successes = []
    failures = []
    lock = threading.Lock()

    def sell_worker():
        connection.close()
        try:
            barrier.wait()
            with transaction.atomic():
                InventoryService.register_exit(
                    inventory=inv,
                    data={
                        "quantity": qty_per_thread,
                        "reference": "RUNNER-CONCURRENT-EXIT",
                        "notes": "Prueba de salida concurrente runner",
                    },
                    user=user,
                )
            with lock:
                successes.append(True)
        except Exception as e:
            with lock:
                failures.append(e)
        finally:
            connection.close()

    threads = [threading.Thread(target=sell_worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    inv.refresh_from_db()
    final_stock = inv.current_stock
    print(
        f"  - Transacciones aprobadas: {len(successes)} (Total vendido: {len(successes) * qty_per_thread})"
    )
    print(f"  - Transacciones rechazadas: {len(failures)} (Stock insuficiente)")
    print(f"  - Stock final en BD: {final_stock}")

    is_ok = final_stock >= 0 and len(successes) == 2 and final_stock == Decimal("2.00")
    status = "✅ EXITOSO (Integridad de stock preservada)" if is_ok else "❌ FALLIDO"
    print(f"  Resultado: {status}")
    return is_ok


def main():
    verify_database_engine()

    print("\n" + "=" * 80)
    print("INICIANDO SUITE DE PRUEBAS DE CONCURRENCIA")
    print("=" * 80)

    # Crear datos de prueba temporales
    with transaction.atomic():
        test_company = CompanyInfo.objects.create(
            business_name="PG Concurrency Co",
            tax_id=f"999{int(time.time()) % 1000000:06d}-9",
        )
        test_user = User.objects.create_user(
            username=f"pg_user_{int(time.time())}",
            email=f"pg_user_{int(time.time())}@test.com",
            password="Password123!",
            document_number=f"DOC{int(time.time()) % 10000000:07d}",
        )
        test_role = Role.objects.create(role_name="Admin", permissions={"all": True})
        CompanyMembership.objects.create(
            user=test_user,
            company=test_company,
            role=test_role,
            is_active=True,
            status=CompanyMembership.MembershipStatus.ACTIVE,
        )
        cat = Category.objects.create(name="PG Test Cat", company=test_company)
        prod = Product.objects.create(
            name="PG Test Product",
            code="PG-01",
            company=test_company,
            category=cat,
            purchase_price=Decimal("10.00"),
            sale_price=Decimal("20.00"),
        )
        inv = Inventory.objects.create(
            product=prod,
            current_stock=Decimal("10.00"),
            minimum_stock=Decimal("1.00"),
        )

    try:
        ok_a = run_scenario_a(company_id=test_company.pk, num_threads=10)
        ok_b = run_scenario_b(inventory_id=inv.pk, user=test_user, num_threads=4)

        print("\n" + "=" * 80)
        print("RESUMEN DE PRUEBAS DE CONCURRENCIA POSTGRESQL")
        print("=" * 80)
        print(
            f"Escenario A (Consecutivos libres de colisión): {'PASÓ' if ok_a else 'FALLÓ'}"
        )
        print(
            f"Escenario B (Protección contra sobreventa):     {'PASÓ' if ok_b else 'FALLÓ'}"
        )

        if ok_a and ok_b:
            print("\n🎉 Todas las pruebas de concurrencia completaron exitosamente.")
            sys.exit(0)
        else:
            print("\n❌ Se detectaron fallos en las pruebas de concurrencia.")
            sys.exit(1)

    finally:
        # Limpieza de registros creados para el runner
        print("\nLimpiando datos temporales de prueba...")
        CompanySequence.objects.filter(company=test_company).delete()
        inv.delete()
        prod.delete()
        cat.delete()
        test_company.delete()
        test_user.delete()
        test_role.delete()
        print("Limpieza completada.")


if __name__ == "__main__":
    main()
