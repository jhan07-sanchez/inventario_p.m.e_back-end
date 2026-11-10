from django.contrib import admin

from apps.cash.models import CashMovement, CashRegister, CashSession, Payment


class CashMovementInline(admin.TabularInline):
    model = CashMovement
    extra = 0
    raw_id_fields = ("payment",)
    readonly_fields = ("created_at",)


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = (
        "id_cash_register",
        "name",
        "company",
        "is_active",
        "created_at",
    )

    list_filter = (
        "company",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "company__business_name",
        "description",
    )

    raw_id_fields = ("company",)

    readonly_fields = ("created_at", "updated_at")


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id_cash_session",
        "company",
        "cash_register",
        "user",
        "status",
        "opening_balance",
        "expected_balance",
        "counted_balance",
        "difference",
        "start_time",
        "end_time",
    )

    list_filter = (
        "company",
        "status",
        "start_time",
        "cash_register",
        "is_active",
    )

    search_fields = (
        "id_cash_session",
        "cash_register__name",
        "user__username",
        "user__email",
        "company__business_name",
        "notes",
    )

    raw_id_fields = ("company", "cash_register", "user")

    readonly_fields = (
        "start_time",
        "created_at",
        "updated_at",
    )

    inlines = [CashMovementInline]


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id_cash_movement",
        "cash_session",
        "movement_type",
        "amount",
        "payment",
        "created_at",
    )

    list_filter = (
        "movement_type",
        "cash_session__company",
        "created_at",
    )

    search_fields = (
        "cash_session__cash_register__name",
        "notes",
    )

    raw_id_fields = ("cash_session", "payment")

    readonly_fields = ("created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id_payment",
        "sale",
        "sale_company",
        "amount",
        "payment_method",
        "status",
        "reference",
        "created_at",
    )

    list_filter = (
        "payment_method",
        "status",
        "created_at",
    )

    search_fields = (
        "sale__sale_number",
        "reference",
        "notes",
    )

    raw_id_fields = ("sale",)

    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Empresa")
    def sale_company(self, obj):
        return obj.sale.company if obj.sale else "-"

