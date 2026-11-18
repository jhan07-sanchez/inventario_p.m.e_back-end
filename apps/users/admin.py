from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CompanyMembership, Role, User, UserRole


class CompanyMembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0
    raw_id_fields = ("company", "role")
    fields = ("company", "role", "is_owner", "status", "is_active")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [CompanyMembershipInline]
    list_display = (
        "id_user",
        "username",
        "document_number",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "document_number",
        "email",
        "first_name",
        "last_name",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )

    ordering = ("id_user",)

    # 1. Quitamos 'role' de los fieldsets porque la relación es vía UserRole
    fieldsets = (
        (
            "Información de acceso",
            {
                "fields": (
                    "username",
                    "password",
                )
            },
        ),
        (
            "Información personal",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "document_number",
                    "phone_number",
                )
            },
        ),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Fechas importantes",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "document_number",
                    "phone_number",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
        "date_joined",
    )

    exclude = ("deleted_at",)

    def get_queryset(self, request):
        """Muestra todos los usuarios, incluyendo los eliminados lógicamente."""
        return User.all_objects.all()


# 2. Sacamos RoleAdmin fuera de CustomUserAdmin (sin sangría)
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id_role",
        "role_name",
        "is_active",
    )

    search_fields = ("role_name",)

    list_filter = ("is_active",)

    ordering = ("id_role",)

    exclude = ("deleted_at",)

    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        """Muestra todos los roles, incluyendo los eliminados lógicamente."""
        return Role.all_objects.all()


# 3. Sacamos UserRoleAdmin fuera y ajustamos list_display y list_filter (sin 'is_active')
@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = (
        "id_user_role",
        "user",
        "role",
    )

    search_fields = (
        "user__username",
        "role__role_name",
    )

    list_filter = ("role",)

    ordering = ("id_user_role",)

    exclude = ("deleted_at",)

    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        """Muestra todas las asignaciones, incluyendo las eliminadas lógicamente."""
        return UserRole.all_objects.all()


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "id_membership",
        "user",
        "company",
        "role",
        "is_owner",
        "status",
        "is_active",
        "created_at",
    )

    list_filter = (
        "status",
        "is_owner",
        "is_active",
        "company",
        "role",
    )

    search_fields = (
        "user__username",
        "user__email",
        "company__business_name",
        "company__tax_id",
        "role__role_name",
    )

    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at")

    raw_id_fields = ("user", "company", "role")
