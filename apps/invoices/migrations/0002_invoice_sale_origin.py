import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0001_initial"),
        ("sales", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="sale",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="invoices",
                to="sales.sale",
                verbose_name="Venta relacionada",
            ),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["sale"], name="invoice_sale_idx"),
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(purchase__isnull=False, sale__isnull=True)
                    | models.Q(purchase__isnull=True, sale__isnull=False)
                ),
                name="invoice_exactly_one_origin",
            ),
        ),
    ]
