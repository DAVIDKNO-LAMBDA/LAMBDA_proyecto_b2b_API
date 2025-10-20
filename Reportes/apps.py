from django.apps import AppConfig


class ReportesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Reportes'
    verbose_name = "📊 Reportes y Facturación"
    
    def ready(self):
        # Importar signals si los hay
        try:
            from . import signals
        except ImportError:
            pass
