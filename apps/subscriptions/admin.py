from django.contrib import admin

from apps.subscriptions.models import Plan, Subscription, SubscriptionPayment


class SubscriptionPaymentInline(admin.TabularInline):
    model = SubscriptionPayment
    extra = 0
    readonly_fields = ("payment_date", "created_at")
    fields = (
        "amount",
        "payment_method",
        "transaction_reference",
        "status",
        "payment_date",
        "invoice_url",
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "id_plan",
        "code",
        "name",
        "price",
        "billing_cycle",
        "max_users",
        "max_products",
        "max_invoices_per_month",
        "is_active",
        "created_at",
    )

    list_filter = (
        "billing_cycle",
        "is_active",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("price", "name")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id_subscription",
        "company",
        "plan",
        "status",
        "start_date",
        "end_date",
        "days_remaining_display",
        "is_valid_display",
        "auto_renew",
        "is_active",
    )

    list_filter = (
        "status",
        "plan",
        "auto_renew",
        "is_active",
        "start_date",
        "end_date",
    )

    search_fields = (
        "company__business_name",
        "company__tax_id",
        "plan__name",
        "plan__code",
    )

    raw_id_fields = ("company", "plan")

    readonly_fields = (
        "start_date",
        "created_at",
        "updated_at",
        "is_valid_display",
        "days_remaining_display",
    )

    inlines = [SubscriptionPaymentInline]

    @admin.display(description="Días Restantes")
    def days_remaining_display(self, obj):
        return obj.days_remaining

    @admin.display(description="¿Vigente?", boolean=True)
    def is_valid_display(self, obj):
        return obj.is_valid


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id_payment",
        "subscription",
        "amount",
        "payment_method",
        "transaction_reference",
        "status",
        "payment_date",
    )

    list_filter = (
        "status",
        "payment_method",
        "payment_date",
    )

    search_fields = (
        "subscription__company__business_name",
        "subscription__company__tax_id",
        "transaction_reference",
    )

    raw_id_fields = ("subscription",)

    readonly_fields = (
        "payment_date",
        "created_at",
        "updated_at",
    )

