"""Documentation schemas for invoice endpoints."""

from .invoice_docs import (
    invoice_cancel_schema,
    invoice_create_schema,
    invoice_delete_schema,
    invoice_issue_schema,
    invoice_list_schema,
    invoice_patch_schema,
    invoice_put_schema,
    invoice_restore_schema,
    invoice_retrieve_schema,
)
from .invoice_template_docs import (
    invoice_template_create_schema,
    invoice_template_delete_schema,
    invoice_template_list_schema,
    invoice_template_patch_schema,
    invoice_template_preview_schema,
    invoice_template_put_schema,
    invoice_template_restore_schema,
    invoice_template_retrieve_schema,
    invoice_template_set_default_schema,
)

__all__ = [
    "invoice_cancel_schema",
    "invoice_create_schema",
    "invoice_delete_schema",
    "invoice_issue_schema",
    "invoice_list_schema",
    "invoice_patch_schema",
    "invoice_put_schema",
    "invoice_restore_schema",
    "invoice_retrieve_schema",
    "invoice_template_create_schema",
    "invoice_template_delete_schema",
    "invoice_template_list_schema",
    "invoice_template_patch_schema",
    "invoice_template_put_schema",
    "invoice_template_restore_schema",
    "invoice_template_retrieve_schema",
    "invoice_template_preview_schema",
    "invoice_template_set_default_schema",
]
