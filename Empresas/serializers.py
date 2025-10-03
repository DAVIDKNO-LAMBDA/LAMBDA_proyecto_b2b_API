from rest_framework import serializers
from .models import Empresa, Area

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = "__all__"

class AreaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Area
        fields = ["id", "nombre", "descripcion", "empresa", "empresa_nombre", "estado"]
