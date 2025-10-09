from rest_framework.permissions import BasePermission

def _auth(u): return bool(u and u.is_authenticated)

class IsAdminEmpresa(BasePermission):
    message = "Se requiere Administrador de Empresa."
    def has_permission(self, request, view):
        u = request.user
        return _auth(u) and bool(getattr(u, "es_admin_empresa", False))

class IsLambdaStaff(BasePermission):
    message = "Se requiere personal autorizado de Lambda."
    def has_permission(self, request, view):
        u = request.user
        return _auth(u) and getattr(u, "is_staff", False) and getattr(getattr(u, "empresa", None), "es_lambda", False)

class IsEmpresaMember(BasePermission):
    """
    Solo permite acceder a pedidos de TU empresa.
    """
    message = "Solo puedes operar sobre pedidos de tu empresa."
    def has_object_permission(self, request, view, obj):
        u = request.user
        return _auth(u) and getattr(u, "empresa_id", None) == getattr(obj, "empresa_id", None)
