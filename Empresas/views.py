from rest_framework import generics, permissions
from .models import Empresa, Area
from .serializers import EmpresaSerializer, AreaSerializer

# --- Vistas para el modelo Empresa ---

class EmpresaListCreateAPIView(generics.ListCreateAPIView):
    """
    Vista para listar (GET) y crear (POST) Empresas.
    """
    queryset = Empresa.objects.filter(deleted_at__isnull=True)
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

class EmpresaRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver detalle (GET), actualizar (PUT/PATCH) y eliminar (DELETE) una Empresa.
    """
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


# --- Vistas para el modelo Area ---

class AreaListCreateAPIView(generics.ListCreateAPIView):
    """
    Vista para listar (GET) y crear (POST) Áreas.
    """
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_queryset(self):
        """
        Filtra las áreas para que un usuario no-superuser solo vea las de su empresa.
        """
        usuario = self.request.user
        if not usuario.is_superuser and hasattr(usuario, 'empresa'):
            return Area.objects.filter(empresa=usuario.empresa)
        return Area.objects.all()

class AreaRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver detalle (GET), actualizar (PUT/PATCH) y eliminar (DELETE) un Área.
    """
    serializer_class = AreaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_queryset(self):
        """
        Filtra las áreas para que un usuario no-superuser solo vea las de su empresa.
        """
        usuario = self.request.user
        if not usuario.is_superuser and hasattr(usuario, 'empresa'):
            return Area.objects.filter(empresa=usuario.empresa)
        return Area.objects.all()
