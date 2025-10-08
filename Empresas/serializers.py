from rest_framework import serializers
from Empresas.models import Empresa, Area

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id", "nombre", "sector", "nit", "nombre_contacto",
            "correo_contacto", "pagar_despues", "es_lambda", "estado", "creado"
        ]
        read_only_fields = ["es_lambda", "estado", "creado"]


class AreaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Area
        fields = [
            "id", "nombre", "descripcion", "tipo",
            "empresa", "empresa_nombre", "estado", "creado"
        ]
        read_only_fields = ["empresa", "empresa_nombre", "estado", "creado"]
