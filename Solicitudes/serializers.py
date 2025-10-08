from rest_framework import serializers
from django.contrib.auth import get_user_model
from Solicitudes.models import Solicitud, ProductoSolicitud, HistorialAprobacion

Usuario = get_user_model()


class ProductoSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoSolicitud
        fields = ["id", "nombre", "cantidad", "unidad", "creado"]


class HistorialAprobacionSerializer(serializers.ModelSerializer):
    usuario_email = serializers.SerializerMethodField()

    class Meta:
        model = HistorialAprobacion
        fields = ["id", "usuario", "usuario_email", "estado_aprobacion", "comentario", "creado"]

    def get_usuario_email(self, obj):
        return obj.usuario.email if obj.usuario else None


class SolicitudSerializer(serializers.ModelSerializer):
    solicitante_email = serializers.CharField(source="solicitante.email", read_only=True)

    class Meta:
        model = Solicitud
        fields = ["id", "empresa", "solicitante", "solicitante_email", "justificacion", "estado", "creado"]


class SolicitudDetalleSerializer(SolicitudSerializer):
    productos = ProductoSolicitudSerializer(many=True, read_only=True)
    historial = HistorialAprobacionSerializer(many=True, read_only=True)

    class Meta(SolicitudSerializer.Meta):
        fields = SolicitudSerializer.Meta.fields + ["productos", "historial"]


class CrearSolicitudSerializer(serializers.Serializer):
    justificacion = serializers.CharField()
    productos = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        allow_empty=False
    )

    def validate(self, data):
        request = self.context["request"]
        empresa = request.user.empresa

        # HU10: La empresa debe tener al menos un validador financiero y uno de abastecimiento
        tiene_logistica = Usuario.objects.filter(
            empresa=empresa, is_active=True, estado=True, user_permissions__codename="valida_logistica"
        ).exists()
        tiene_finanzas = Usuario.objects.filter(
            empresa=empresa, is_active=True, estado=True, user_permissions__codename="valida_financiero"
        ).exists()

        if not tiene_logistica or not tiene_finanzas:
            raise serializers.ValidationError(
                "La empresa debe tener al menos un validador de abastecimiento y uno financiero antes de crear solicitudes."
            )

        # Normalizamos productos
        productos = data.get("productos", [])
        if not productos:
            raise serializers.ValidationError("Debe registrar al menos un producto.")

        # Validaciones simples de producto
        normalizados = []
        for p in productos:
            nombre = p.get("nombre")
            cantidad = p.get("cantidad")
            unidad = p.get("unidad", "unidad")
            if not nombre or not cantidad:
                raise serializers.ValidationError("Cada producto debe incluir 'nombre' y 'cantidad'.")
            try:
                cantidad = int(cantidad)
            except Exception:
                raise serializers.ValidationError("La cantidad debe ser un número entero positivo.")
            if cantidad <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
            normalizados.append({"nombre": nombre, "cantidad": cantidad, "unidad": unidad})

        data["productos"] = normalizados
        return data

    def create(self, validated_data):
        request = self.context["request"]
        empresa = request.user.empresa

        solicitud = Solicitud.objects.create(
            empresa=empresa,
            solicitante=request.user,
            justificacion=validated_data["justificacion"],
            estado="pendiente_abastecimiento"
        )

        prods = [
            ProductoSolicitud(solicitud=solicitud, **p) for p in validated_data["productos"]
        ]
        ProductoSolicitud.objects.bulk_create(prods)

        HistorialAprobacion.objects.create(
            solicitud=solicitud,
            usuario=request.user,
            estado_aprobacion="creada",
            comentario="Solicitud creada por el solicitante"
        )
        return solicitud
