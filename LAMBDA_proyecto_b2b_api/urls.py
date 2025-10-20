# LAMBDA_proyecto_b2b_api/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Apps
    path("api/", include("Empresas.urls")),
    path("api/usuarios/", include("Usuarios.urls")),
    path("api/productos/", include("Productos.urls")),
    path("api/solicitudes/", include("Solicitudes.urls")),
    path("api/pedidos/", include("Pedidos.urls")),
    path("api/reportes/", include("Reportes.urls")),  # ← NUEVO
]

