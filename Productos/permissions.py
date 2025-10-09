from rest_framework.permissions import BasePermission

def _is_auth(u):
    return bool(u and u.is_authenticated)

class IsLambdaStaff(BasePermission):
    """
    Solo personal de Lambda (is_staff=True y su empresa es Lambda).
    Usar para CRUD de catálogo y movimientos de entrada.
    """
    message = "Se requiere personal autorizado de Lambda."

    def has_permission(self, request, view):
        u = request.user
        return _is_auth(u) and getattr(u, "is_staff", False) and getattr(getattr(u, "empresa", None), "es_lambda", False)
