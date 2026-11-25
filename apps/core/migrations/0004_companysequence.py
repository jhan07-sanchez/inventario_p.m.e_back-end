# Generated manually for SaaS company sequences
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("company_info", "0002_companyinfo_owner_user_companyinfo_status_and_more"),
        ("core", "0003_auditlog_company_auditlog_audit_comp_created_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanySequence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Fecha de actualización",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Fecha de eliminación",
                    ),
                ),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("SALE", "Venta"),
                            ("PURCHASE", "Compra"),
                            ("INVOICE", "Factura"),
                            ("POS_TICKET", "Ticket POS"),
                        ],
                        help_text="Tipo de documento comercial que utiliza este consecutivo.",
                        max_length=50,
                        verbose_name="Tipo de documento",
                    ),
                ),
                (
                    "prefix",
                    models.CharField(
                        default="VTA",
                        help_text="Prefijo alfanumérico para el documento (ej. VTA, FAC, CMP).",
                        max_length=10,
                        verbose_name="Prefijo",
                    ),
                ),
                (
                    "current_number",
                    models.PositiveBigIntegerField(
                        default=0,
                        help_text="Último número entero emitido para este tipo de documento.",
                        verbose_name="Número actual",
                    ),
                ),
                (
                    "padding",
                    models.PositiveSmallIntegerField(
                        default=6,
                        help_text="Cantidad mínima de dígitos con ceros a la izquierda (ej. 6 produce 000001).",
                        verbose_name="Relleno de ceros",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        help_text="Organización a la que pertenece esta secuencia.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sequences",
                        to="company_info.companyinfo",
                        verbose_name="Empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Secuencia Empresarial",
                "verbose_name_plural": "Secuencias Empresariales",
                "db_table": "company_sequences",
            },
        ),
        migrations.AddIndex(
            model_name="companysequence",
            index=models.Index(
                fields=["company", "document_type"],
                name="idx_company_seq_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="companysequence",
            constraint=models.UniqueConstraint(
                fields=("company", "document_type"),
                name="unique_company_sequence_type",
            ),
        ),
    ]
