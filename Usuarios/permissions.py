from rest_framework.permissions import BasePermission
from Empresas.roles import build_group_name, ROL_ADMIN

def _is_auth(u):
    return bool(u and u.is_authenticated)

class IsAdminEmpresaByGroup(BasePermission):
    message = "Se requiere Administrador de Empresa."
    def has_permission(self, request, view):
        u = request.user
        if not _is_auth(u) or not getattr(u, "empresa_id", None):
            return False
        gname = build_group_name(u.empresa_id, ROL_ADMIN)
        return u.groups.filter(name=gname).exists()
