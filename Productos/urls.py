from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    # =============================================
    # PRODUCTOS
    # =============================================
    path('', views.ProductoListAPIView.as_view(), name='producto-list'),
    path('crear/', views.ProductoCreateAPIView.as_view(), name='producto-create'),
    path('<int:pk>/', views.ProductoDetailAPIView.as_view(), name='producto-detail'),
    
    # Endpoints especiales
    path('bajo-minimo/', views.productos_bajo_minimo, name='productos-bajo-minimo'),
    path('<int:pk>/stock/', views.stock_producto, name='producto-stock'),
    path('<int:pk>/reservar/', views.reservar_stock, name='reservar-stock'),
    path('<int:pk>/liberar/', views.liberar_stock, name='liberar-stock'),
    
    # =============================================
    # MOVIMIENTOS
    # =============================================
    path('movimientos/', views.MovimientoInventarioListAPIView.as_view(), name='movimiento-list'),
    path('movimientos/crear/', views.MovimientoInventarioCreateAPIView.as_view(), name='movimiento-create'),
]
