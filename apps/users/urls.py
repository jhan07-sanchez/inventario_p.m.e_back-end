from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.users.views.auth_view import (
    AuthLoginView,
    AuthLogoutView,
    AuthRefreshView,
    MeView,
)
from apps.users.views.role.role_view import RoleViewSet
from apps.users.views.security_view import (
    SecurityContextView,
    SecurityDashboardView,
    SecurityNavigationView,
    SecurityPermissionCatalogView,
)
from apps.users.views.user_roles.user_role_viewset import UserRoleViewSet
from apps.users.views.users.user_viewset import UserViewSet

router = DefaultRouter()

router.register(
    r"users",
    UserViewSet,
    basename="users",
)

router.register(
    r"roles",
    RoleViewSet,
    basename="roles",
)

router.register(
    r"user-roles",
    UserRoleViewSet,
    basename="user-roles",
)


urlpatterns = [
    path("", include(router.urls)),
    path(
        "auth/login/",
        AuthLoginView.as_view(),
        name="auth-login",
    ),
    path(
        "auth/refresh/",
        AuthRefreshView.as_view(),
        name="auth-refresh",
    ),
    path(
        "auth/me/",
        MeView.as_view(),
        name="auth-me",
    ),
    path(
        "auth/logout/",
        AuthLogoutView.as_view(),
        name="auth-logout",
    ),
    path(
        "security/context/",
        SecurityContextView.as_view(),
        name="security-context",
    ),
    path(
        "security/navigation/",
        SecurityNavigationView.as_view(),
        name="security-navigation",
    ),
    path(
        "security/dashboard/",
        SecurityDashboardView.as_view(),
        name="security-dashboard",
    ),
    path(
        "security/permissions/",
        SecurityPermissionCatalogView.as_view(),
        name="security-permission-catalog",
    ),
]
