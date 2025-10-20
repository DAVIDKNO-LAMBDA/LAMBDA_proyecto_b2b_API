"""
Middleware personalizado para el control de activación de usuarios
"""
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class ActivacionUsuarioMiddleware:
    """
    Middleware que verifica si los usuarios empresa han activado su cuenta
    antes de permitir acceso a endpoints protegidos
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que NO requieren verificación de activación
        self.excluded_paths = [
            '/admin/',
            '/api/auth/login/',
            '/api/auth/token/',
            '/api/usuarios/activar/',
            '/api/auth/refresh/',
            '/swagger/',
            '/redoc/',
            '/health/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # Ejecutar middleware antes de la vista
        response = self.process_request(request)
        if response:
            return response
            
        # Continuar con la vista
        response = self.get_response(request)
        return response

    def process_request(self, request):
        """
        Verifica si el usuario autenticado puede usar el sistema
        """
        # Saltar verificación para rutas excluidas
        if any(request.path.startswith(path) for path in self.excluded_paths):
            return None
            
        # Solo verificar usuarios autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # Superusuarios siempre pueden acceder
        if request.user.is_superuser:
            return None
            
        # Verificar si el usuario puede autenticarse según nuestras reglas
        if not request.user.puede_autenticarse():
            logger.warning(
                f"Acceso denegado a usuario no activado: {request.user.email} "
                f"(estado: {request.user.estado})"
            )
            
            return JsonResponse({
                'error': 'Cuenta no activada',
                'detail': 'Debes activar tu cuenta mediante el enlace enviado a tu correo electrónico.',
                'estado': request.user.estado,
                'requiere_activacion': request.user.requiere_activacion(),
                'action_required': 'activar_cuenta'
            }, status=status.HTTP_403_FORBIDDEN)
            
        return None