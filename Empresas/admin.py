from django.contrib import admin
from .models import Empresa, Area

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Empresa.
    """
    list_display = ['id', 'nombre', 'nit', 'sector', 'pagar_despues', 'created_at']
    search_fields = ['nombre', 'nit']
    list_filter = ['pagar_despues', 'es_lambda', 'created_at']
    ordering = ['-created_at']

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Area.
    """
    list_display = ['id', 'nombre', 'empresa', 'created_at']
    list_filter = ['empresa', 'created_at']
    
    search_fields = ['nombre', 'empresa__nombre']
    ordering = ['-created_at']
