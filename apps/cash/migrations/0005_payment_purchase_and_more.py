# Generated manually for Payment to Purchase explicit relation
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "cash",
            "0004_remove_cashsession_unique_open_session_per_user_and_more",
        ),
        (
            "purchases",
            "0002_purchase_company_purchase_purch_comp_status_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="purchase",
            field=models.ForeignKey(
                blank=True,
                help_text="Orden de compra a la que se aplica este pago o egreso.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payments",
                to="purchases.purchase",
                verbose_name="Compra Asociada",
            ),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["purchase"], name="payments_purchas_9ba048_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["purchase", "status"], name="idx_pay_purch_status"
            ),
        ),
    ]
