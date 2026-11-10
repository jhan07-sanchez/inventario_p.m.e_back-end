from django.contrib import admin

from apps.inventory.models import Inventory, InventoryMovement


class InventoryMovementInline(admin.TabularInline):
    model = InventoryMovement
    extra = 0
    readonly_fields = (
        "movement_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "reference",
        "user",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "id_inventory",
        "product",
        "product_company",
        "current_stock",
        "minimum_stock",
        "maximum_stock",
        "stock_status",
        "is_active",
        "updated_at",
    )

    search_fields = (
        "product__name",
        "product__code",
        "product__barcode",
        "product__company__business_name",
    )

    list_filter = (
        "product__company",
        "is_active",
        "product__category",
    )

    raw_id_fields = ("product",)

    readonly_fields = ("created_at", "updated_at")

    inlines = [InventoryMovementInline]

    @admin.display(description="Empresa")
    def product_company(self, obj):
        return obj.product.company if obj.product else "-"

    @admin.display(description="Estado de Stock")
    def stock_status(self, obj):
        if obj.current_stock <= obj.minimum_stock:
            return "⚠️ Bajo Stock"
        if obj.maximum_stock and obj.current_stock > obj.maximum_stock:
            return "📈 Sobre-stock"
        return "✅ Óptimo"


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    """
    Kardex de movimientos de inventario (Auditoría de existencias).
    """

    list_display = (
        "id_movement",
        "inventory_product",
        "movement_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "reference",
        "user",
        "created_at",
    )

    list_filter = (
        "movement_type",
        "inventory__product__company",
        "created_at",
    )

    search_fields = (
        "inventory__product__name",
        "inventory__product__code",
        "reference",
        "notes",
        "user__username",
    )

    raw_id_fields = ("inventory", "supplier", "user")

    readonly_fields = (
        "inventory",
        "movement_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "reference",
        "notes",
        "supplier",
        "user",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Producto")
    def inventory_product(self, obj):
        return obj.inventory.product.name if obj.inventory and obj.inventory.product else "-"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
