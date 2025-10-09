from rest_framework import generics, permissions, status
from rest_framework.response import Response

from Empresas.models import Empresa, Area
from Empresas.serializers import EmpresaSerializer, AreaSerializer
from Usuarios.permissions import IsAdminEmpresa, IsJefeDeEstaAreaOrAdminEmpresa


# ============================================================
# 🔹 Listar Empresas (solo Admin Lambda/staff)
# ============================================================
class EmpresaListView(generics.ListAPIView):
    queryset = Empresa.objects.filter(estado=True)
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAdminUser]


# ============================================================
# 🔹 Crear Empresa Externa (solo Admin Lambda/staff)
# ============================================================
class EmpresaCreateView(generics.CreateAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(es_lambda=False)


# ============================================================
# 🔹 Editar Empresa (solo Admin Lambda/staff)
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
# 🔹 Crear Área (solo Admin Empresa)
# ============================================================
class AreaCreateView(generics.CreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminEmpresa]

    def perform_create(self, serializer):
        # fuerza la empresa del usuario autenticado
        serializer.save(empresa=self.request.user.empresa)


# ============================================================
# 🔹 Editar Área (Admin Empresa o Jefe de esa Área)
# ============================================================
class AreaUpdateView(generics.UpdateAPIView):
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated, IsJefeDeEstaAreaOrAdminEmpresa]
    lookup_field = "pk"

    def get_queryset(self):
        # restringe a las áreas de la empresa del usuario
        return Area.objects.filter(empresa=self.request.user.empresa)

    def update(self, request, *args, **kwargs):
        area = self.get_object()  # dispara object-level permissions
        self.check_object_permissions(request, area)

        data = request.data.copy()
        data.pop("empresa", None)  # no permitir cambiar empresa por API

        serializer = self.get_serializer(area, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": f"Área '{area.nombre}' actualizada correctamente."},
            status=status.HTTP_200_OK
        )
