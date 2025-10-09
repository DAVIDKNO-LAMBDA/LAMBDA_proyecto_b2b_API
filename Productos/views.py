from rest_framework import generics, permissions
from Productos.models import Producto
from Productos.serializers import ProductoSerializer, MovimientoEntradaSerializer
from Productos.permissions import IsLambdaStaff


# =========================
# Productos (Catálogo)
# =========================
class ProductoListCreateView(generics.ListCreateAPIView):
    queryset = Producto.objects.filter(estado=True)
    serializer_class = ProductoSerializer

    def get_permissions(self):
        if self.request.method.lower() == "post":
            return [permissions.IsAuthenticated(), IsLambdaStaff()]
        return [permissions.IsAuthenticated()]


class ProductoDetalleView(generics.RetrieveAPIView):
    queryset = Producto.objects.filter(estado=True)
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"


class ProductoUpdateView(generics.UpdateAPIView):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated, IsLambdaStaff]
    lookup_field = "pk"


# =========================
# Movimientos (solo ENTRADAS)
# =========================
class MovimientoEntradaCreateView(generics.CreateAPIView):
    """
    Registra entradas de inventario (HU17 base).
    """
    serializer_class = MovimientoEntradaSerializer
    permission_classes = [permissions.IsAuthenticated, IsLambdaStaff]
