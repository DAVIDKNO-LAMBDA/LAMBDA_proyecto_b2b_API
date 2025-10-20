from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Empresa, Area
from .serializers import EmpresaSerializer, AreaSerializer
import logging

logger = logging.getLogger(__name__)

# --- Vistas para el modelo Empresa ---

class EmpresaListCreateAPIView(generics.ListCreateAPIView):
    """
    Vista para listar (GET) y crear (POST) Empresas.
    Al crear una empresa, automáticamente crea las áreas base requeridas.
    """
    queryset = Empresa.objects.filter(deleted_at__isnull=True)
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    
    def perform_create(self, serializer):
        """
        Sobrescribe la creación para auto-crear áreas base
        """
        with transaction.atomic():
            # Crear la empresa
            empresa = serializer.save()
            
            # 🆕 Auto-crear áreas base requeridas
            areas_base = [
                {
                    'nombre': 'Abastecimiento',
                    'descripcion': 'Área base encargada de gestión de inventario y stock interno de la empresa',
                    'es_area_base': True
                },
                {
                    'nombre': 'Finanzas', 
                    'descripcion': 'Área base encargada de validación presupuestal y gestión financiera',
                    'es_area_base': True
                }
            ]
            
            areas_creadas = []
            for area_data in areas_base:
                area = Area.objects.create(
                    nombre=area_data['nombre'],
                    descripcion=area_data['descripcion'],
                    tipo='abastecimiento' if area_data['nombre'] == 'Abastecimiento' else 'financiera',
                    empresa=empresa,
                    es_area_base=area_data['es_area_base']
                )
                areas_creadas.append(area)
                
            logger.info(f"✅ Empresa {empresa.nombre} creada con {len(areas_creadas)} áreas base")
            
    def create(self, request, *args, **kwargs):
        """
        Sobrescribe create para devolver información de áreas creadas
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Obtener empresa creada con sus áreas
        empresa = serializer.instance
        areas = Area.objects.filter(empresa=empresa)
        
        response_data = {
            'empresa': serializer.data,
            'areas_base_creadas': [
                {
                    'id': area.id,
                    'nombre': area.nombre,
                    'descripcion': area.descripcion
                } for area in areas
            ],
            'mensaje': f'Empresa creada exitosamente con {areas.count()} áreas base'
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)

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
