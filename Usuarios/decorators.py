# Usuarios/decorators.py
from functools import wraps
from typing import Iterable, Type, Callable, List

from rest_framework.permissions import BasePermission, IsAuthenticated


# ============================================================
# Mixin para que DRF lea permisos declarados en el handler
# ============================================================
def _as_instances(perms: Iterable[Type[BasePermission] | BasePermission]) -> List[BasePermission]:
    out: List[BasePermission] = []
    for p in perms:
        out.append(p() if isinstance(p, type) else p)
    return out


class MethodPermissionsMixin:
    """
    Permite declarar permisos específicos por método (get/post/patch/...) usando decoradores.
    Si el handler tiene atributo _permission_classes, DRF usará esos;
    si no, caerá a permission_classes de la clase.
    """
    def get_permissions(self):
        handler = getattr(self, self.request.method.lower(), None)
        if handler is not None and hasattr(handler, "_permission_classes"):
            return _as_instances(getattr(handler, "_permission_classes"))
        return [perm() for perm in getattr(self, "permission_classes", [])]


# ============================================================
# Decorador simple para adjuntar permission_classes al handler
# ============================================================
def permissions_required(*permission_classes: Type[BasePermission]) -> Callable:
    """
    @permissions_required(IsAuthenticated, IsAdminEmpresa)
    NO valida aquí; solo declara los permisos que DRF evaluará.
    """
    def deco(func):
        # guardamos la lista de permissions para que el Mixin los lea
        setattr(func, "_permission_classes", tuple(permission_classes))

        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # DRF llamará get_permissions() antes de entrar aquí
            return func(self, request, *args, **kwargs)
        return wrapper
    return deco


# ============================================================
# Decorador por codenames nativos (opcional)
# ============================================================
class _HasPerms(BasePermission):
    """
    Evalúa codenames nativos mediante user.has_perms/has_perm,
    pero ejecutándose dentro del ciclo normal de DRF.
    La vista (o el handler) debe tener:
      - _required_perms_all: list[str]
      - _required_perms_any: list[str]
    """
    message = "No tienes los permisos requeridos."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        all_perms = getattr(view, "_required_perms_all", []) or []
        any_perms = getattr(view, "_required_perms_any", []) or []

        if all_perms and not user.has_perms(all_perms):
            return False
        if any_perms and not any(user.has_perm(p) for p in any_perms):
            return False
        return True


def perms_required(*, all: Iterable[str] = (), any: Iterable[str] = ()):
    """
    @perms_required(all=["app.codename1","app.codename2"])
    @perms_required(any=["app.codename3"])
    Inyecta IsAuthenticated + _HasPerms al handler (DRF los validará).
    """
    def deco(func):
        setattr(func, "_required_perms_all", list(all or []))
        setattr(func, "_required_perms_any", list(any or []))

        # construimos la lista final de permission classes para este handler
        base = list(getattr(func, "_permission_classes", ()))
        if IsAuthenticated not in base:
            base.append(IsAuthenticated)
        base.append(_HasPerms)
        setattr(func, "_permission_classes", tuple(base))

        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            return func(self, request, *args, **kwargs)
        return wrapper
    return deco


# ============================================================
# Atajos para tus permisos custom
# ============================================================
from Usuarios.permissions import IsAdminEmpresa, IsJefeDeEstaAreaOrAdminEmpresa

def require_admin_empresa(func):
    """
    @require_admin_empresa -> IsAuthenticated + IsAdminEmpresa
    """
    return permissions_required(IsAuthenticated, IsAdminEmpresa)(func)

def require_jefe_o_admin(func):
    """
    @require_jefe_o_admin -> IsAuthenticated + IsJefeDeEstaAreaOrAdminEmpresa
    """
    return permissions_required(IsAuthenticated, IsJefeDeEstaAreaOrAdminEmpresa)(func)




from Usuarios.permissions import (
    IsAdminEmpresa, IsJefeDeEstaAreaOrAdminEmpresa,
    IsSolicitante, IsValidadorAbastecimiento, IsValidadorFinanciero
)

def require_admin_empresa(func):
    from rest_framework.permissions import IsAuthenticated
    return permissions_required(IsAuthenticated, IsAdminEmpresa)(func)

def require_jefe_o_admin(func):
    from rest_framework.permissions import IsAuthenticated
    return permissions_required(IsAuthenticated, IsJefeDeEstaAreaOrAdminEmpresa)(func)

def require_solicitante(func):
    from rest_framework.permissions import IsAuthenticated
    return permissions_required(IsAuthenticated, IsSolicitante)(func)

def require_validador_abastecimiento(func):
    from rest_framework.permissions import IsAuthenticated
    return permissions_required(IsAuthenticated, IsValidadorAbastecimiento)(func)

def require_validador_financiero(func):
    from rest_framework.permissions import IsAuthenticated
    return permissions_required(IsAuthenticated, IsValidadorFinanciero)(func)

