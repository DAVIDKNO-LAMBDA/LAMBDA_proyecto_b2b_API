from rest_framework import generics, permissions
from Productos.models import Producto
from Productos.serializers import ProductoSerializer, MovimientoEntradaSerializer

class ProductoListCreateView(generics.ListCreateAPIView):
    queryset = Producto.objects.filter(estado=True)
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

class ProductoDetalleView(generics.RetrieveAPIView):
    queryset = Producto.objects.filter(estado=True)
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    lookup_field = "pk"

class ProductoUpdateView(generics.UpdateAPIView):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    lookup_field = "pk"

class MovimientoEntradaCreateView(generics.CreateAPIView):
    serializer_class = MovimientoEntradaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
