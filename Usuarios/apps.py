class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Usuarios"
    verbose_name = "Usuarios"

    def ready(self):
        import Usuarios.signals  # noqa
