from functools import wraps
from rest_framework.response import Response
from rest_framework import status

def requiere_permiso(permiso):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return Response({"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED)
            if not user.has_perm(permiso):
                return Response({"detail": f"No tienes permiso: {permiso}"}, status=status.HTTP_403_FORBIDDEN)
            return view_func(self, request, *args, **kwargs)
        return _wrapped_view
    return decorator

def requiere_empresa_activa(view_func):
    @wraps(view_func)
    def _wrapped_view(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.empresa or not user.empresa.estado:
            return Response({"detail": "La empresa no está habilitada."}, status=status.HTTP_403_FORBIDDEN)
        return view_func(self, request, *args, **kwargs)
    return _wrapped_view
