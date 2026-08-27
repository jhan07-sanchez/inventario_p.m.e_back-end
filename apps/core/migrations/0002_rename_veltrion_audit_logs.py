from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "veltrion_audit_logs" '
                'RENAME TO "inventario_pme_audit_logs";'
            ),
            reverse_sql=(
                'ALTER TABLE "inventario_pme_audit_logs" '
                'RENAME TO "veltrion_audit_logs";'
            ),
        ),
    ]
