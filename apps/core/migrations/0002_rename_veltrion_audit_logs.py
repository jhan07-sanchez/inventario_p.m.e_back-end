from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Lo que realmente ejecuta en PostgreSQL (lo que ya tenías)
            database_operations=[
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
            ],
            # Le informa a Django que el nombre del modelo/tabla cambió
            state_operations=[
                migrations.AlterModelTable(
                    name="auditlog",
                    table="inventario_pme_audit_logs",
                ),
            ],
        )
    ]
