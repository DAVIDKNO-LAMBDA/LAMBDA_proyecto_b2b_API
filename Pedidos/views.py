from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from Pedidos.models import Pedido
from Pedidos.serializers import (
    PedidoSerializer,
    PedidoCreateSerializer,
    ConfigurarPagoSerializer,
)
from Pedidos.permissions import IsAdminEmpresa, IsLambdaStaff, IsEmpresaMember


# ==============================
# Listar / Detalle
# ==============================
class PedidoListView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # cada usuario ve solo pedidos de su empresa
        return Pedido.objects.filter(empresa=self.request.user.empresa).order_by("-creado")


class PedidoDetailView(generics.RetrieveAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmpresaMember]
    lookup_field = "pk"

    def get_queryset(self):
        return Pedido.objects.filter(empresa=self.request.user.empresa)


# ==============================
# Crear pedido (HU14)
# ==============================
class PedidoCreateView(generics.CreateAPIView):
    serializer_class = PedidoCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminEmpresa]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save()
        out = PedidoSerializer(pedido).data
        return Response(out, status=status.HTTP_201_CREATED)


# ==============================
# Configurar condiciones de pago (HU15) – solo Lambda staff
# ==============================
class ConfigurarPagoView(generics.UpdateAPIView):
    serializer_class = ConfigurarPagoSerializer
    permission_classes = [permissions.IsAuthenticated, IsLambdaStaff]
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        ser = self.get_serializer(data=request.data, context={"pedido": pedido, "request": request})
        ser.is_valid(raise_exception=True)
        pedido = ser.save()
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_200_OK)
