from rest_framework import serializers
from django.utils import timezone
from .models import Usuario, ActivationToken

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        exclude = ["password", "user_permissions", "groups", "last_login", "is_superuser", "is_staff"]

class EmpleadoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "celular", "cargo", "area", "rol", "estado"]

    def validate_email(self, value):
        empresa = self.context["request"].user.empresa
        if Usuario.objects.filter(empresa=empresa, email=value).exists():
            raise serializers.ValidationError("Correo ya registrado en esta empresa.")
        return value

    def create(self, validated_data):
        empresa = self.context["request"].user.empresa
        user = Usuario.objects.create(empresa=empresa, **validated_data)
        user.set_unusable_password()
        user.save()
        ActivationToken.create_for_user(user)
        return user

class EmpleadoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "celular", "cargo", "area", "rol", "estado"]

class ActivacionSerializer(serializers.Serializer):
    token = serializers.CharField()
    first_name = serializers.CharField()
    celular = serializers.CharField()
    cargo = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        token_str = attrs["token"]
        try:
            tok = ActivationToken.objects.select_related("user").get(token=token_str)
        except ActivationToken.DoesNotExist:
            raise serializers.ValidationError("Token inválido.")
        if not tok.is_valid:
            raise serializers.ValidationError("Token expirado o usado.")
        attrs["token_obj"] = tok
        return attrs

    def save(self):
        tok = self.validated_data["token_obj"]
        user = tok.user
        user.first_name = self.validated_data["first_name"]
        user.celular = self.validated_data["celular"]
        user.cargo = self.validated_data["cargo"]
        user.rol = "admin_empresa"
        user.set_password(self.validated_data["password"])
        user.estado = True
        user.save()
        tok.used_at = timezone.now()
        tok.save()
        return user
