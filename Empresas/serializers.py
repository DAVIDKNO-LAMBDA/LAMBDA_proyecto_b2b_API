from rest_framework import serializers
from Empresas.models import Empresa, Area


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id",
            "nombre",
            "sector",
            "nit",
            "nombre_contacto",
            "correo_contacto",
            "pagar_despues",
            "es_lambda",
            "estado",
            "creado",
        ]
        # es_lambda lo fija el flujo (Admin Lambda); estado/creado solo lectura (BaseModel)
        read_only_fields = ["es_lambda", "estado", "creado"]


class AreaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    # 🔹 NUEVO: permitir asignar jefe (id de Usuario) y validarlo
    # Nota: la vista setea empresa desde request.user.empresa; empresa es read_only.
    class Meta:
        model = Area
        fields = [
            "id",
            "nombre",
            "descripcion",
            "tipo",
            "jefe",
            "empresa",
            "empresa_nombre",
            "estado",
            "creado",
        ]
        read_only_fields = ["empresa", "empresa_nombre", "estado", "creado"]

    def validate_jefe(self, user):
        """
        Si se envía un jefe, debe pertenecer a la MISMA empresa del request.
        """
        if not user:
            return user
        request = self.context.get("request")
        if not request or not hasattr(request.user, "empresa"):
            # En context siempre pasamos request desde la vista; si no, no validamos aquí.
            return user
        if user.empresa_id != request.user.empresa_id:
            raise serializers.ValidationError("El jefe debe pertenecer a tu misma empresa.")
        return user

    def validate(self, attrs):
        """
        Validación extra por si actualizan 'jefe' en un área ya existente:
        jefe.empresa == area.empresa (coherencia con model.clean()).
        """
        jefe = attrs.get("jefe", None)
        instance = getattr(self, "instance", None)
        # Determinar empresa destino (en create la pone la vista; en update viene del instance)
        empresa = None
        if instance:
            empresa = instance.empresa
        else:
            # En create, empresa la setea perform_create(); aquí solo cruzamos con request si existe
            req = self.context.get("request")
            if req and hasattr(req.user, "empresa"):
                empresa = req.user.empresa

        if jefe and empresa and jefe.empresa_id != empresa.id:
            raise serializers.ValidationError({"jefe": "El jefe debe pertenecer a la misma empresa del área."})

        return attrs
