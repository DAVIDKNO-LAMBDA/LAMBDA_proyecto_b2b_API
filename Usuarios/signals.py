from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import Usuario
from Base.correos import enviar_correo_activacion_usuario
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Usuario)
def enviar_correo_activacion_signal(sender, instance, created, **kwargs):
    """
    Signal que se ejecuta DESPUÉS de crear un usuario
    Envía correo de activación solo a usuarios de empresas externas (no Lambda)
    """
    if created and instance.empresa and instance.token_activacion:
        try:
            # Obtener el creador desde el atributo temporal (si existe)
            creador = getattr(instance, '_creador', None)
            
            # Enviar correo de activación
            resultado = enviar_correo_activacion_usuario(instance, creador)
            
            if resultado:
                logger.info(f"✅ [SIGNAL] Correo de activación enviado a {instance.email}")
            else:
                logger.error(f"❌ [SIGNAL] Error enviando correo a {instance.email}")
        
        except Exception as e:
            logger.error(f"❌ [SIGNAL] Excepción: {str(e)}")


@receiver(post_save, sender=Usuario)
def asignar_rol_inicial_signal(sender, instance, created, update_fields, **kwargs):
    """
    Signal que asigna rol inicial cuando el usuario ACTIVA su cuenta
    Solo se ejecuta cuando el estado cambia de 'pendiente_activacion' a 'activo'
    """
    # Solo ejecutar si es una actualización (no creación)
    if not created and instance.estado == 'activo':
        # Verificar si ya tiene roles asignados
        if instance.groups.exists():
            logger.info(f"ℹ️ [SIGNAL] Usuario {instance.email} ya tiene roles asignados")
            return
        
        try:
            # Determinar qué rol asignar
            if instance.es_primer_usuario:
                # Primer usuario de la empresa → Admin Empresa
                grupo = Group.objects.get(name='Admin Empresa')
                instance.groups.add(grupo)
                logger.info(f"✅ [SIGNAL] Rol 'Admin Empresa' asignado a {instance.email}")
            
            elif instance.area:
                # Usuario con área asignada → Jefe de Área
                grupo = Group.objects.get(name='Jefe de Área')
                instance.groups.add(grupo)
                logger.info(f"✅ [SIGNAL] Rol 'Jefe de Área' asignado a {instance.email}")
            
            else:
                # Usuario sin área → Empleado básico
                grupo = Group.objects.get(name='Empleado')
                instance.groups.add(grupo)
                logger.info(f"✅ [SIGNAL] Rol 'Empleado' asignado a {instance.email}")
        
        except Group.DoesNotExist as e:
            logger.error(f"❌ [SIGNAL] Error: Grupo no encontrado - {str(e)}")
            logger.warning("⚠️ Ejecuta: python manage.py bootstrap_roles")