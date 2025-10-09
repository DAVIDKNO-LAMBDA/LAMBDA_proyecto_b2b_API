from django.urls import path
from Productos.views import (
    ProductoListCreateView,
    ProductoDetalleView,
    ProductoUpdateView,
    MovimientoEntradaCreateView,
)

urlpatterns = [
    # /api/productos/
    path("", ProductoListCreateView.as_view(), name="productos-listar-crear"),
    path("<int:pk>/", ProductoDetalleView.as_view(), name="productos-detalle"),
    path("<int:pk>/editar/", ProductoUpdateView.as_view(), name="productos-editar"),

    # /api/productos/movimientos/entrada/
    path("movimientos/entrada/", MovimientoEntradaCreateView.as_view(), name="movimientos-entrada-crear"),
]
