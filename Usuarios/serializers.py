from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from Empresas.models import Area
from Usuarios.models import ActivacionUsuario

User = get_user_model()


# =========================
# Detalle / Edición Usuario
# =========================
class UsuarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nombres",
            "apellidos",
            "celular",
            "cargo",
            "empresa",
            "empresa_nombre",
            "area",
            "area_nombre",
            "is_active",
            # Flags de rol (si existen en tu modelo)
            "es_admin_empresa",
            "es_solicitante",
            "validador_abastecimiento",
            "validador_financiero",
            "creado",
        ]
        read_only_fields = ["email", "empresa", "empresa_nombre", "creado"]

    def to_representation(self, instance):
        """
        Si el modelo no tiene alguno de los flags (por si tu User aún no los trae),
        los exponemos como False para no romper el cliente.
        """
        rep = super().to_representation(instance)
        for f in ["es_admin_empresa", "es_solicitante", "validador_abastecimiento", "validador_financiero"]:
            if f not in rep:
                rep[f] = bool(getattr(instance, f, False))
        return rep

    def validate_area(self, area):
        """
        En edición, si cambian el área, debe pertenecer a la misma empresa del usuario.
        """
        if area is None:
            return area
        instance = getattr(self, "instance", None)
        if instance and area.empresa_id != instance.empresa_id:
            raise serializers.ValidationError("El área debe pertenecer a la misma empresa del usuario.")
        return area


# =========================
# Crear Empleado
# =========================
class CrearEmpleadoSerializer(serializers.ModelSerializer):
    """
    Reglas:
      - Admin Empresa: puede crear en cualquier área de SU empresa; puede marcar es_admin_empresa.
      - Jefe de Área: solo puede crear en su área; NO puede marcar es_admin_empresa.
    La señal enviará el correo de activación.
    """
    class Meta:
        model = User
        fields = [
            "email",
            "nombres",
            "apellidos",
            "celular",
            "cargo",
            "area",
            # flags (si existen en tu modelo)
            "es_solicitante",
            "validador_abastecimiento",
            "validador_financiero",
            "es_admin_empresa",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "nombres": {"required": True},
            "cargo": {"required": True},
            "area": {"required": True},
        }

    # --- Validaciones de negocio ---
    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("Ya existe un usuario con ese correo."))
        return value

    def validate_area(self, area: Area):
        request = self.context.get("request")
        if not request or not hasattr(request.user, "empresa"):
            return area

        # El área debe ser de la misma empresa del admin/jefe que crea
        if area.empresa_id != request.user.empresa_id:
            raise serializers.ValidationError("El área debe pertenecer a tu empresa.")
        return area

    def validate(self, attrs):
        request = self.context.get("request")
        if not request:
            return attrs

        es_admin_solicitado = bool(attrs.get("es_admin_empresa", False))

        # Admin Empresa: puede crear en cualquier área de su empresa y marcar admin
        if getattr(request.user, "es_admin_empresa", False):
            return attrs

        # Jefe de Área: solo en su área y NO puede marcar admin
        # Para esto, asumimos que request.user es jefe del área a cargo (Area.jefe)
        area = attrs.get("area")
        if not area or area.jefe_id != request.user.id:
            raise serializers.ValidationError("Solo puedes crear empleados en tu área a cargo.")
        if es_admin_solicitado:
            raise serializers.ValidationError("No puedes asignar 'es_admin_empresa'.")

        return attrs

    # --- Creación ---
    def create(self, validated_data):
        request = self.context["request"]
        empresa = request.user.empresa

        # Extraer flags si no existen en el modelo (por si tu User aún no los trae)
        def _pop_flag(data, key, default=False):
            if key in [f.name for f in User._meta.get_fields()]:
                return data.get(key, default)
            # si el campo no existe en el modelo, lo ignoramos
            validated_data.pop(key, None)
            return default

        es_admin_empresa = _pop_flag(validated_data, "es_admin_empresa", False)
        es_solicitante = _pop_flag(validated_data, "es_solicitante", True)
        val_abast = _pop_flag(validated_data, "validador_abastecimiento", False)
        val_fin = _pop_flag(validated_data, "validador_financiero", False)

        usuario = User.objects.create_user(
            email=validated_data["email"],
            nombres=validated_data["nombres"],
            apellidos=validated_data.get("apellidos", ""),
            cargo=validated_data["cargo"],
            empresa=empresa,
            area=validated_data["area"],
            password=None,  # sin password: lo define al activar
        )
        # Estado de activación
        usuario.is_active = False
        usuario.set_unusable_password()

        # Setear flags si existen en el modelo
        for k, v in {
            "es_admin_empresa": es_admin_empresa,
            "es_solicitante": es_solicitante,
            "validador_abastecimiento": val_abast,
            "validador_financiero": val_fin,
        }.items():
            if hasattr(usuario, k):
                setattr(usuario, k, v)

        usuario.save()
        return usuario


# =========================
# Activar Cuenta con token
# =========================
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
        if activacion.fecha_expiracion and activacion.fecha_expiracion < activacion.creado:
            # por si hay datos corruptos
            raise serializers.ValidationError("El enlace de activación es inválido.")
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
