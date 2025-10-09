from django.urls import path
from Pedidos.views import (
    PedidoListView,
    PedidoDetailView,
    PedidoCreateView,
    ConfigurarPagoView,
)

urlpatterns = [
    path("", PedidoListView.as_view(), name="pedidos-listar"),
    path("crear/", PedidoCreateView.as_view(), name="pedidos-crear"),
    path("<int:pk>/", PedidoDetailView.as_view(), name="pedidos-detalle"),
    path("<int:pk>/configurar-pago/", ConfigurarPagoView.as_view(), name="pedidos-configurar-pago"),
]
