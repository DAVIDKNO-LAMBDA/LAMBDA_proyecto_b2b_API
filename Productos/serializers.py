from rest_framework import serializers
from Productos.models import Producto, MovimientoInventario

class ProductoSerializer(serializers.ModelSerializer):
    stock_disponible = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id", "nombre", "descripcion", "precio", "umbral_minimo",
            "estado", "creado", "stock_disponible",
        ]
        read_only_fields = ["estado", "creado", "stock_disponible"]

    def get_stock_disponible(self, obj: Producto):
        return obj.stock_disponible()

class MovimientoEntradaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = ["id", "producto", "cantidad", "nota", "creado"]
        read_only_fields = ["id", "creado"]

    def validate(self, data):
        producto = data.get("producto")
        if not producto or not producto.estado:
            raise serializers.ValidationError("Producto inválido o inactivo.")
        return data

    def create(self, validated_data):
        request = self.context["request"]
        return MovimientoInventario.objects.create(
            producto=validated_data["producto"],
            tipo=MovimientoInventario.TIPO_ENTRADA,
            cantidad=validated_data["cantidad"],
            usuario=request.user,
            nota=validated_data.get("nota", ""),
        )
