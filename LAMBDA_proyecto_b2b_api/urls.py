from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Admin de Django
    path("admin/", admin.site.urls),

    # Endpoints de Empresas y Áreas
    path("api/", include("Empresas.urls")),

    # Endpoints de Usuarios
    path("api/", include("Usuarios.urls")),

    # Autenticación JWT
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
