from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Panel de administración de Django
    path("admin/", admin.site.urls),

    # Rutas locales
    path("api/", include("Empresas.urls")),
    path("api/", include("Usuarios.urls")),

    # Autenticación con JWT
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
]
