from rest_framework import generics, permissions, status
from rest_framework.response import Response
from Empresas.models import Empresa, Area
from Empresas.serializers import EmpresaSerializer, AreaSerializer

class EmpresaListView(generics.ListAPIView):
    queryset = Empresa.objects.filter(estado=True)
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

class EmpresaCreateView(generics.CreateAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    def perform_create(self, serializer):
        serializer.save(es_lambda=False)

class EmpresaUpdateView(generics.UpdateAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    lookup_field = "pk"
    def update(self, request, *args, **kwargs):
        empresa = self.get_object()
        ser = self.get_serializer(empresa, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": f"Empresa '{empresa.nombre}' actualizada correctamente."}, status=status.HTTP_200_OK)

class AreaCreateView(generics.CreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class AreaUpdateView(generics.UpdateAPIView):
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    lookup_field = "pk"
    def get_queryset(self):
        return Area.objects.filter(empresa=self.request.user.empresa)
    def update(self, request, *args, **kwargs):
        area = self.get_object()
        data = request.data.copy()
        data.pop("empresa", None)
        ser = self.get_serializer(area, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": f"Área '{area.nombre}' actualizada correctamente."}, status=status.HTTP_200_OK)
