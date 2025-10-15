from django.contrib import admin
from .models import Empresa, Area

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Empresa.
    """
    list_display = ('nombre', 'nit', 'sector', 'estado', 'pagar_despues')
    search_fields = ('nombre', 'nit')
    list_filter = ('estado', 'sector', 'pagar_despues')
    ordering = ('nombre',)

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Area.
    """
    list_display = ('nombre', 'empresa', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado', 'empresa')
    ordering = ('empresa', 'nombre')
