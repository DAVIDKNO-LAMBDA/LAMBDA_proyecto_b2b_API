from rest_framework import generics, permissions, status
from rest_framework.response import Response
from Empresas.models import Empresa, Area
from Empresas.serializers import EmpresaSerializer, AreaSerializer
from Usuarios.decorators import permiso_requerido


# ============================================================
# 🔹 Listar Empresas (solo Admin Lambda)
# ============================================================
class EmpresaListView(generics.ListAPIView):
    queryset = Empresa.objects.filter(estado=True)
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAdminUser]


# ============================================================
# 🔹 Crear Empresa Externa (solo Admin Lambda)
# ============================================================
class EmpresaCreateView(generics.CreateAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        empresa = serializer.save(es_lambda=False)
        return empresa


# ============================================================
# 🔹 Editar Empresa (solo Admin Lambda)
# ============================================================
class EmpresaUpdateView(generics.UpdateAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        empresa = self.get_object()
        serializer = self.get_serializer(empresa, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": f"Empresa '{empresa.nombre}' actualizada correctamente."},
            status=status.HTTP_200_OK
        )


# ============================================================
# 🔹 Crear Área (AdminEmpresa)
# ============================================================
class AreaCreateView(generics.CreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @permiso_requerido("Usuarios.es_admin_empresa")
    def perform_create(self, serializer):
        empresa = self.request.user.empresa
        serializer.save(empresa=empresa)


# ============================================================
# 🔹 Editar Área (AdminEmpresa)
# ============================================================
class AreaUpdateView(generics.UpdateAPIView):
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Area.objects.filter(empresa=self.request.user.empresa)

    @permiso_requerido("Usuarios.es_admin_empresa")
    def update(self, request, *args, **kwargs):
        area = self.get_object()
        data = request.data.copy()
        data.pop("empresa", None)
        serializer = self.get_serializer(area, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": f"Área '{area.nombre}' actualizada correctamente."},
            status=status.HTTP_200_OK
        )
