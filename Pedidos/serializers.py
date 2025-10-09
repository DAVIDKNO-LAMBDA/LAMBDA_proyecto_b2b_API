from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers

from Pedidos.models import Pedido, PedidoItem
from Productos.models import Producto


class PedidoItemInSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.filter(estado=True))
    cantidad = serializers.IntegerField(min_value=1)


class PedidoItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = PedidoItem
        fields = ["id", "producto", "producto_nombre", "cantidad", "precio_unitario", "subtotal", "creado"]
        read_only_fields = ["precio_unitario", "subtotal", "creado"]


class PedidoSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    items = PedidoItemSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id", "numero", "empresa", "empresa_nombre", "creado_por",
            "estado", "modalidad_pago", "fecha_vencimiento", "aprobado_pago_por",
            "total", "creado",
            "items",
        ]
        read_only_fields = ["numero", "empresa", "creado_por", "estado", "aprobado_pago_por", "total", "creado"]


class PedidoCreateSerializer(serializers.Serializer):
    """
    HU14: Crear pedido validando stock. Queda en 'pendiente_pago'.
    """
    items = PedidoItemInSerializer(many=True)
    modalidad_pago = serializers.ChoiceField(choices=Pedido.MODALIDADES, default=Pedido.PAGO_INMEDIATO)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        modalidad = attrs.get("modalidad_pago")
        fv = attrs.get("fecha_vencimiento")
        empresa = self.context["request"].user.empresa

        if modalidad == Pedido.PAGO_DIFERIDO:
            if not empresa.pagar_despues:
                raise serializers.ValidationError("La empresa no está autorizada para pago diferido.")
            if not fv:
                raise serializers.ValidationError({"fecha_vencimiento": "Requerida para pago diferido."})
            if fv > (timezone.localdate() + timedelta(days=60)):
                raise serializers.ValidationError({"fecha_vencimiento": "No puede exceder 60 días desde hoy."})
        else:
            # inmediato: ignoramos fv
            attrs["fecha_vencimiento"] = None
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        empresa = request.user.empresa

        pedido = Pedido.objects.create(
            empresa=empresa,
            creado_por=request.user,
            modalidad_pago=validated_data["modalidad_pago"],
            fecha_vencimiento=validated_data.get("fecha_vencimiento"),
            estado=Pedido.EST_PENDIENTE_PAGO,
        )

        # Crear items (valida stock disponible en clean())
        for it in validated_data["items"]:
            PedidoItem.objects.create(
                pedido=pedido,
                producto=it["producto"],
                cantidad=it["cantidad"],
                precio_unitario=it["producto"].precio,
            )

        pedido.recalcular_total()
        return pedido


class ConfigurarPagoSerializer(serializers.Serializer):
    """
    HU15: Configurar condiciones de pago por staff de Lambda.
    """
    modalidad_pago = serializers.ChoiceField(choices=Pedido.MODALIDADES)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        pedido: Pedido = self.context["pedido"]
        modalidad = attrs.get("modalidad_pago")
        fv = attrs.get("fecha_vencimiento")

        if modalidad == Pedido.PAGO_DIFERIDO:
            if not pedido.empresa.pagar_despues:
                raise serializers.ValidationError("La empresa no está autorizada para pago diferido.")
            if not fv:
                raise serializers.ValidationError({"fecha_vencimiento": "Requerida para pago diferido."})
            from datetime import timedelta
            from django.utils import timezone
            if fv > (timezone.localdate() + timedelta(days=60)):
                raise serializers.ValidationError({"fecha_vencimiento": "No puede exceder 60 días desde hoy."})
        else:
            attrs["fecha_vencimiento"] = None
        return attrs

    def save(self, **kwargs):
        pedido: Pedido = self.context["pedido"]
        data = self.validated_data
        pedido.modalidad_pago = data["modalidad_pago"]
        pedido.fecha_vencimiento = data.get("fecha_vencimiento")
        pedido.aprobado_pago_por = self.context["request"].user  # staff Lambda
        pedido.full_clean()
        pedido.save(update_fields=["modalidad_pago", "fecha_vencimiento", "aprobado_pago_por"])
        return pedido
