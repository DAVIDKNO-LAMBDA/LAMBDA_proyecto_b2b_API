from rest_framework import serializers
from .models import Empresa

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = "nombre", "sector", "nit", "correo_contacto", "pagar_despues"
        

