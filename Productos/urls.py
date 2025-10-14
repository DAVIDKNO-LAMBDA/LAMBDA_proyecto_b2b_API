from django.urls import path
from Productos.views import (
    ProductoListCreateView, ProductoDetalleView, ProductoUpdateView,
    MovimientoEntradaCreateView,
)

urlpatterns = [
    path("", ProductoListCreateView.as_view(), name="productos-listar-crear"),
    path("<int:pk>/", ProductoDetalleView.as_view(), name="productos-detalle"),
    path("<int:pk>/editar/", ProductoUpdateView.as_view(), name="productos-editar"),
    path("movimientos/entrada/", MovimientoEntradaCreateView.as_view(), name="movimientos-entrada-crear"),
]
