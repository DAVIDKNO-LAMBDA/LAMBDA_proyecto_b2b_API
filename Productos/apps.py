from django.apps import AppConfig

class ProductosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Productos"

    def ready(self):
        from . import signals  # noqa
