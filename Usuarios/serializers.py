from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from Empresas.models import Area
from Usuarios.models import ActivacionUsuario

User = get_user_model()

class UsuarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)

    class Meta:
        model = User
        fields = [
            "id","email","nombres","apellidos","celular","cargo",
            "empresa","empresa_nombre","area","area_nombre",
            "is_active","creado",
        ]
        read_only_fields = ["email","empresa","empresa_nombre","creado"]

    def validate_area(self, area):
        if area is None:
            return area
        instance = getattr(self, "instance", None)
        if instance and area.empresa_id != instance.empresa_id:
            raise serializers.ValidationError("El área debe pertenecer a la misma empresa del usuario.")
        return area

class CrearEmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "nombres", "apellidos", "celular", "cargo", "area"]
        extra_kwargs = {
            "email": {"required": True},
            "nombres": {"required": True},
            "cargo": {"required": True},
            "area": {"required": True},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("Ya existe un usuario con ese correo."))
        return value

    def validate_area(self, area: Area):
        request = self.context.get("request")
        if request and hasattr(request.user, "empresa") and area.empresa_id != request.user.empresa_id:
            raise serializers.ValidationError("El área debe pertenecer a tu empresa.")
        return area

    def create(self, validated_data):
        request = self.context["request"]
        empresa = request.user.empresa
        usuario = User.objects.create_user(
            email=validated_data["email"],
            nombres=validated_data["nombres"],
            apellidos=validated_data.get("apellidos", ""),
            cargo=validated_data["cargo"],
            empresa=empresa,
            area=validated_data["area"],
            password=None,
        )
        usuario.is_active = False
        usuario.set_unusable_password()
        usuario.save()
        return usuario

class ActivarCuentaSerializer(serializers.Serializer):
    nombres = serializers.CharField(max_length=255)
    celular = serializers.CharField(max_length=20)
    cargo = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        usuario = self.context.get("usuario")
        activacion = self.context.get("activacion")
        if not usuario or not activacion:
            raise serializers.ValidationError("Token inválido o contexto incompleto.")
        if activacion.usado:
            raise serializers.ValidationError("Este enlace ya fue usado.")
        return attrs

    def save(self, **kwargs):
        usuario = self.context["usuario"]
        activacion = self.context["activacion"]
        data = self.validated_data

        usuario.nombres = data["nombres"]
        usuario.celular = data["celular"]
        usuario.cargo = data["cargo"]
        usuario.set_password(data["password"])
        usuario.is_active = True
        usuario.save()

        activacion.usado = True
        activacion.save(update_fields=["usado"])
        return usuario
