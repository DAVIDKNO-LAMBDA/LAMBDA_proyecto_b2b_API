from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from Empresas.models import Area
from Usuarios.models import ActivacionUsuario
from .models import Usuario
from django.contrib.auth.models import Group, Permission

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
    apellidos = serializers.CharField(max_length=255, required=False, allow_blank=True)
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
        if data.get("apellidos"):
            usuario.apellidos = data["apellidos"]
        usuario.celular = data["celular"]
        usuario.cargo = data["cargo"]
        usuario.set_password(data["password"])
        usuario.is_active = True
        usuario.save()

        activacion.usado = True
        activacion.save(update_fields=["usado"])
        return usuario

class PermisoSerializer(serializers.ModelSerializer):
    """Serializer para mostrar permisos de Django"""
    nombre_completo = serializers.SerializerMethodField()
    app = serializers.CharField(source='content_type.app_label', read_only=True)
    modelo = serializers.CharField(source='content_type.model', read_only=True)
    
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'nombre_completo', 'app', 'modelo']
    
    def get_nombre_completo(self, obj):
        return f"{obj.content_type.app_label}.{obj.codename}"


class GrupoSerializer(serializers.ModelSerializer):
    """Serializer para mostrar grupos/roles con sus permisos"""
    permisos = PermisoSerializer(many=True, read_only=True, source='permissions')
    cantidad_permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'cantidad_permisos', 'permisos']
    
    def get_cantidad_permisos(self, obj):
        return obj.permissions.count()


class AsignarAreaSerializer(serializers.Serializer):
    """Serializer para cambiar el área de un usuario (HU08)"""
    area_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_area_id(self, value):
        """Validar que el área exista y esté activa"""
        if value:
            try:
                area = Area.objects.get(id=value, estado='activa', deleted_at__isnull=True)
                # Validar que el área sea de la misma empresa
                usuario = self.context.get('usuario')
                if usuario and area.empresa_id != usuario.empresa_id:
                    raise serializers.ValidationError(
                        "El área debe pertenecer a la misma empresa del usuario"
                    )
                return area
            except Area.DoesNotExist:
                raise serializers.ValidationError("Área no encontrada o inactiva")
        return None


class AsignarPermisosEspecialesSerializer(serializers.Serializer):
    """
    Serializer para asignar permisos especiales (HU09)
    Ejemplo: validador_finanzas, validador_abastecimiento
    """
    validador_finanzas = serializers.BooleanField(required=False, default=False)
    validador_abastecimiento = serializers.BooleanField(required=False, default=False)
    puede_crear_solicitudes = serializers.BooleanField(required=False, default=False)
    limite_aprobacion = serializers.IntegerField(
        required=False, 
        min_value=0,
        help_text="Límite en pesos para aprobación financiera"
    )
    
    def validate(self, data):
        """Validar combinaciones de permisos"""
        # Si es validador financiero, debe tener límite
        if data.get('validador_finanzas') and not data.get('limite_aprobacion'):
            raise serializers.ValidationError({
                "limite_aprobacion": "Los validadores financieros deben tener un límite de aprobación"
            })
        
        return data


class UsuarioConPermisosSerializer(serializers.ModelSerializer):
    """Serializer extendido que incluye permisos detallados"""
    nombre_completo = serializers.CharField(read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    roles = serializers.SerializerMethodField()
    permisos_detalle = serializers.SerializerMethodField()
    validadores = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'email', 'nombres', 'apellidos', 'nombre_completo',
            'cargo', 'celular', 'empresa', 'empresa_nombre',
            'area', 'area_nombre', 'estado', 'es_primer_usuario',
            'roles', 'permisos_personalizados', 'permisos_detalle',
            'validadores', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'estado', 'es_primer_usuario', 'created_at', 'updated_at'
        ]
    
    def get_roles(self, obj):
        """Obtiene los grupos/roles del usuario"""
        return obj.obtener_roles()
    
    def get_permisos_detalle(self, obj):
        """Obtiene información completa de permisos"""
        return obj.obtener_permisos_detalle()
    
    def get_validadores(self, obj):
        """Información rápida de validadores (para HU10)"""
        return {
            'es_validador_finanzas': obj.es_validador_finanzas(),
            'es_validador_abastecimiento': obj.es_validador_abastecimiento(),
            'limite_aprobacion': obj.obtener_limite_aprobacion()
        }
