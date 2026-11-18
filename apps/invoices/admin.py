from django.contrib import admin

from apps.invoices.models import Invoice, InvoiceItem, InvoiceTemplate


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "document_type",
        "is_default",
        "is_active",
        "created_at",
    )
    list_filter = (
        "company",
        "document_type",
        "is_default",
        "is_active",
    )
    search_fields = (
        "name",
        "company__business_name",
    )
    raw_id_fields = ("company",)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    raw_id_fields = ("product",)
    readonly_fields = ("subtotal",)
    fields = ("product", "quantity", "unit_price", "discount", "tax", "subtotal")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "company",
        "document_type",
        "status",
        "issue_date",
        "total",
        "is_active",
        "created_at",
    )

    list_filter = (
        "company",
        "document_type",
        "status",
        "is_active",
        "created_at",
    )

    search_fields = (
        "invoice_number",
        "company__business_name",
        "company_name_snapshot",
        "company_tax_id_snapshot",
    )

    raw_id_fields = ("company", "template", "purchase", "sale")

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice",
        "product",
        "quantity",
        "unit_price",
        "discount",
        "tax",
        "subtotal",
    )

    list_filter = (
        "invoice__company",
        "invoice__document_type",
    )

    search_fields = (
        "invoice__invoice_number",
        "product__name",
        "description",
    )

    raw_id_fields = ("invoice", "product")
