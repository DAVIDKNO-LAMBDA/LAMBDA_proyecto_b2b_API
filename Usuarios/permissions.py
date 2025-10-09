# Usuarios/permissions.py
from rest_framework.permissions import BasePermission
from Empresas.models import Area

def _is_auth(user):
    return bool(user and user.is_authenticated)

class IsAdminEmpresa(BasePermission):
    """
    Acceso para usuarios con flag es_admin_empresa=True.
    """
    message = "Se requiere ser Administrador de Empresa."
    def has_permission(self, request, view):
        u = request.user
        return _is_auth(u) and getattr(u, "es_admin_empresa", False)


class IsJefeDeEstaAreaOrAdminEmpresa(BasePermission):
    """
    Permite si el usuario es admin de empresa o el jefe asignado del 'Area' objetivo.
    Se usa en Update de Área (object-level).
    """
    message = "Se requiere ser Admin de la Empresa o Jefe de esta área."

    def has_permission(self, request, view):
        return _is_auth(request.user)

    def has_object_permission(self, request, view, obj: Area):
        u = request.user
        if getattr(u, "es_admin_empresa", False):
            return True
        # jefe exacto de esa área
        return bool(obj.jefe_id and obj.jefe_id == u.id)


class IsSolicitante(BasePermission):
    """
    Puede crear solicitudes internas (HU10).
    """
    message = "No tienes permiso para crear solicitudes."
    def has_permission(self, request, view):
        u = request.user
        return _is_auth(u) and getattr(u, "es_solicitante", False)


class IsValidadorAbastecimiento(BasePermission):
    """
    Puede validar solicitudes como abastecimiento (HU12).
    """
    message = "No tienes permiso de validador de abastecimiento."
    def has_permission(self, request, view):
        u = request.user
        return _is_auth(u) and getattr(u, "validador_abastecimiento", False)


class IsValidadorFinanciero(BasePermission):
    """
    Puede validar solicitudes como financiero (HU13).
    """
    message = "No tienes permiso de validador financiero."
    def has_permission(self, request, view):
        u = request.user
        return _is_auth(u) and getattr(u, "validador_financiero", False)
