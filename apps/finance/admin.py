from django.contrib import admin

from apps.finance.models import (
    FinancialAccount,
    FinancialCategory,
    FinancialMovement,
    FinancialReconciliation,
    FinancialTransfer,
)


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "account_type",
        "bank_name",
        "account_number",
        "current_balance",
        "currency",
        "is_active",
    )
    list_filter = ("company", "account_type", "is_active", "currency")
    search_fields = ("name", "bank_name", "account_number", "company__business_name")
    raw_id_fields = ("company",)


@admin.register(FinancialCategory)
class FinancialCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "category_type", "is_active")
    list_filter = ("company", "category_type", "is_active")
    search_fields = ("name", "company__business_name")
    raw_id_fields = ("company",)


@admin.register(FinancialMovement)
class FinancialMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id_financial_movement",
        "account",
        "category",
        "movement_type",
        "amount",
        "payment_method",
        "status",
        "movement_date",
    )
    list_filter = ("movement_type", "status", "payment_method", "movement_date")
    search_fields = ("description", "reference", "account__name")


@admin.register(FinancialTransfer)
class FinancialTransferAdmin(admin.ModelAdmin):
    list_display = (
        "id_financial_transfer",
        "source_account",
        "destination_account",
        "amount",
        "transfer_date",
        "status",
    )
    list_filter = ("status", "transfer_date")
    search_fields = ("source_account__name", "destination_account__name", "reference")


@admin.register(FinancialReconciliation)
class FinancialReconciliationAdmin(admin.ModelAdmin):
    list_display = (
        "id_reconciliation",
        "account",
        "start_date",
        "end_date",
        "statement_balance",
        "book_balance",
        "difference",
        "status",
    )
    list_filter = ("status", "end_date")
    search_fields = ("account__name", "notes")

