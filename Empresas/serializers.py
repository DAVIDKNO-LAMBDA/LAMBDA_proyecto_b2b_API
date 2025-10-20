from rest_framework import serializers
from .models import Empresa, Area

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            'id',
            'nombre',
            'sector',
            'nit',
            'correo_contacto',
            'estado',
            # --- CORRECCIÓN AQUÍ ---
            # El campo se llama 'fecha_creacion' en el modelo, no 'creado'.
            'fecha_creacion', 
        ]
        read_only_fields = ['id', 'fecha_creacion']

class EmpresaListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados de empresas"""
    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'nit', 'sector', 'estado']

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'
