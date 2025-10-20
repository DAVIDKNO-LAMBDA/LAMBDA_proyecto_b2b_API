from django.apps import AppConfig


class PedidosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Pedidos'
    verbose_name = 'Gestión de Pedidos'
    
    def ready(self):
        """
        Importa signals cuando la app esté lista
        """
        from . import signals
