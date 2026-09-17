from django.contrib import admin

from apps.invoices.models import Invoice, InvoiceItem, InvoiceTemplate


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "document_type", "is_default", "is_active", "created_at")
    list_filter = ("document_type", "is_default", "is_active")
    search_fields = ("name",)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    raw_id_fields = ("product",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "document_type",
        "status",
        "issue_date",
        "total",
        "is_active",
        "created_at",
    )
    list_filter = ("document_type", "status", "is_active")
    search_fields = ("invoice_number",)
    raw_id_fields = ("template", "purchase")
    inlines = [InvoiceItemInline]
