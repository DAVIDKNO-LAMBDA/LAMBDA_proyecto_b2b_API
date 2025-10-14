from rest_framework import serializers
from Empresas.models import Empresa, Area

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id", "nombre", "sector", "nit", "nombre_contacto",
            "correo_contacto", "pagar_despues", "es_lambda", "estado", "creado",
        ]
        read_only_fields = ["es_lambda", "estado", "creado"]


class AreaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Area
        fields = [
            "id", "nombre", "descripcion", "tipo",
            "jefe", "empresa", "empresa_nombre", "estado", "creado",
        ]
        read_only_fields = ["empresa", "empresa_nombre", "estado", "creado"]

    def validate_jefe(self, user):
        if not user:
            return user
        request = self.context.get("request")
        if request and hasattr(request.user, "empresa") and user.empresa_id != request.user.empresa_id:
            raise serializers.ValidationError("El jefe debe pertenecer a tu misma empresa.")
        return user

    def validate(self, attrs):
        jefe = attrs.get("jefe", None)
        instance = getattr(self, "instance", None)
        empresa = instance.empresa if instance else getattr(self.context.get("request").user, "empresa", None)
        if jefe and empresa and jefe.empresa_id != empresa.id:
            raise serializers.ValidationError({"jefe": "El jefe debe pertenecer a la misma empresa del área."})
        return attrs
