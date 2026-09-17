from django.contrib import admin
from apps.purchases.models import Purchase, PurchaseDetail

class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 0
    readonly_fields = ("subtotal",)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id_purchase", "supplier", "status", "issue_date", "subtotal", "total")
    list_filter = ("status", "issue_date", "is_active")
    search_fields = ("supplier__business_name", "supplier__document_number")
    inlines = [PurchaseDetailInline]
