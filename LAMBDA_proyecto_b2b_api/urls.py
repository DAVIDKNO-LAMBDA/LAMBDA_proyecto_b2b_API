# LAMBDA_proyecto_b2b_api/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    # === API ===
    path("api/empresas/", include("Empresas.urls")),     # → Empresas/urls.py SIN repetir "empresas/"
    path("api/usuarios/", include("Usuarios.urls")),     # → Usuarios/urls.py SIN repetir "usuarios/"
   # path("api/solicitudes/", include("Solicitudes.urls")),  # cuando esté lista
    path("api/productos/", include("Productos.urls")),

    # Auth JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
]
