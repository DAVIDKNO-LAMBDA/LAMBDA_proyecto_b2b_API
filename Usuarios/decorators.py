from rest_framework.response import Response
from rest_framework import status
from functools import wraps

def permiso_requerido(codename):
    """
    Decorador para validar si el usuario autenticado tiene un permiso específico.
    Ejemplo: @permiso_requerido('Usuarios.es_admin_empresa')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not request.user.has_perm(codename):
                return Response(
                    {"detail": f"No tienes permiso para realizar esta acción ({codename})."},
                    status=status.HTTP_403_FORBIDDEN
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
