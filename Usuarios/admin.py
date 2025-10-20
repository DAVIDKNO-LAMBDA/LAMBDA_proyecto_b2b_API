from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, ActivacionUsuario

@admin.register(Usuario)
class UserAdmin(BaseUserAdmin):
    """
    Configuración del admin para el modelo Usuario personalizado.
    """
    list_display = ('email', 'nombres', 'apellidos', 'empresa', 'is_staff', 'is_active')
    search_fields = ('email', 'nombres', 'apellidos')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'empresa')
    ordering = ('email',)
    
    # Campos que se mostrarán en el formulario de edición
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('nombres', 'apellidos', 'cargo', 'celular')}),
        ('Pertenencia', {'fields': ('empresa', 'area')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Campos que se mostrarán al crear un usuario
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombres', 'apellidos', 'password', 'password_confirm', 'empresa', 'area', 'cargo'),
        }),
    )

@admin.register(ActivacionUsuario)
class ActivacionUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'token', 'usado', 'fecha_expiracion')
    readonly_fields = ('token',)
