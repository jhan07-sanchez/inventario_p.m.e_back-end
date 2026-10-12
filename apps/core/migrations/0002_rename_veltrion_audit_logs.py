from django.db import migrations


def rename_audit_logs(apps, schema_editor):
    table_names = schema_editor.connection.introspection.table_names()
    model = apps.get_model("core", "AuditLog")
    if "veltrion_audit_logs" in table_names and "inventario_pme_audit_logs" not in table_names:
        schema_editor.alter_db_table(model, "veltrion_audit_logs", "inventario_pme_audit_logs")
    elif "inventario-pme_audit_logs" in table_names and "inventario_pme_audit_logs" not in table_names:
        schema_editor.alter_db_table(model, "inventario-pme_audit_logs", "inventario_pme_audit_logs")


def reverse_rename_audit_logs(apps, schema_editor):
    table_names = schema_editor.connection.introspection.table_names()
    model = apps.get_model("core", "AuditLog")
    if "inventario_pme_audit_logs" in table_names and "veltrion_audit_logs" not in table_names:
        schema_editor.alter_db_table(model, "inventario_pme_audit_logs", "veltrion_audit_logs")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(rename_audit_logs, reverse_rename_audit_logs),
            ],
            state_operations=[
                migrations.AlterModelTable(
                    name="auditlog",
                    table="inventario_pme_audit_logs",
                ),
            ],
        )
    ]
