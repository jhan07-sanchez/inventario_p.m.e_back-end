from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migración que aplica los cambios del módulo de ventas:

    - customer: deja de ser obligatorio (null=True, blank=True).
    - sale_type: nuevo campo ADMIN/POS.
    - amount_received: monto recibido del cliente (POS efectivo).
    - change_amount: cambio/vuelto entregado al cliente (POS efectivo).
    """

    dependencies = [
        ("sales", "0001_initial"),
    ]

    operations = [
        # 1. Hacer customer nullable
        migrations.AlterField(
            model_name="sale",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Cliente asociado a la venta. "
                    "NULL indica venta a Consumidor Final (POS)."
                ),
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sales",
                to="customers.customer",
                verbose_name="Cliente",
            ),
        ),
        # 2. Agregar sale_type
        migrations.AddField(
            model_name="sale",
            name="sale_type",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Administrativa"),
                    ("POS", "Punto de Venta"),
                ],
                db_index=True,
                default="ADMIN",
                help_text="ADMIN: flujo dos pasos. POS: venta rápida desde caja.",
                max_length=10,
                verbose_name="Tipo de venta",
            ),
        ),
        # 3. Agregar amount_received
        migrations.AddField(
            model_name="sale",
            name="amount_received",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Efectivo recibido del cliente (POS efectivo).",
                max_digits=12,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0.00"))
                ],
                verbose_name="Monto recibido",
            ),
        ),
        # 4. Agregar change_amount
        migrations.AddField(
            model_name="sale",
            name="change_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Vuelto/cambio entregado al cliente (POS efectivo).",
                max_digits=12,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0.00"))
                ],
                verbose_name="Cambio",
            ),
        ),
    ]
