from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Usuarios'
    verbose_name = 'Gestión de Usuarios'
    
    def ready(self):
        """
        Este método se ejecuta cuando Django inicia
        Importa los signals para que se registren
        """
        import Usuarios.signals  # ← IMPORTANTE: Importar signals
