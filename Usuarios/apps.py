from django.apps import AppConfig

class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Usuarios"

    def ready(self):
        # Carga señales de Usuarios (activación por correo, etc.)
        from . import signals  # noqa: F401
