from Usuarios.models import Usuario

class CrearEmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["email", "nombres", "apellidos", "cargo", "area",
                "es_solicitante", "validador_abastecimiento", "validador_financiero"]

    def create(self, validated_data):
        request = self.context["request"]
        empresa = request.user.empresa

        usuario = Usuario.objects.create_user(
            email=validated_data["email"],
            nombres=validated_data["nombres"],
            apellidos=validated_data.get("apellidos", ""),
            cargo=validated_data["cargo"],
            empresa=empresa,
            area=validated_data["area"],
            password=None,  # SIN password: lo define al activar
        )
        usuario.is_active = False
        usuario.set_unusable_password()
        usuario.es_solicitante = validated_data.get("es_solicitante", True)
        usuario.validador_abastecimiento = validated_data.get("validador_abastecimiento", False)
        usuario.validador_financiero = validated_data.get("validador_financiero", False)
        usuario.save(update_fields=[
            "is_active", "password", "es_solicitante",
            "validador_abastecimiento", "validador_financiero"
        ])
        return usuario

