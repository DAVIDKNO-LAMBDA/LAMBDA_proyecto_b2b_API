from rest_framework import serializers
from Usuarios.models import Usuario, ActivacionUsuario
from Empresas.models import Empresa, Area


class UsuarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "nombres", "apellidos", "email", "celular", "cargo",
            "empresa", "empresa_nombre", "area", "area_nombre",
            "is_active", "estado", "creado"
        ]
        read_only_fields = ["empresa_nombre", "area_nombre", "estado", "creado"]


class CrearUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["nombres", "apellidos", "email", "cargo", "area"]


class ActivacionSerializer(serializers.Serializer):
    nombres = serializers.CharField()
    celular = serializers.CharField()
    cargo = serializers.CharField()
    password = serializers.CharField(write_only=True)
