from django.apps import AppConfig

class EmpresasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Empresas"

    def ready(self):
        from . import signals  # registra los receivers
