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
                
                # ASIGNAR PERMISOS JSON PARA ADMIN EMPRESA
                instance.permisos_personalizados = {
                    'puede_crear_solicitudes': True,
                    'validador_finanzas': True,
                    'validador_abastecimiento': True,
                    'puede_crear_usuarios': True,
                    'puede_ver_todas_solicitudes': True,
                    'limite_aprobacion': 1000000  # Sin límite
                }
                instance.save(update_fields=['permisos_personalizados'])
                
                logger.info(f"✅ [SIGNAL] Rol 'Admin Empresa' asignado a {instance.email}")
            
            elif instance.area:
                # Usuario con área asignada → Jefe de Área
                grupo = Group.objects.get(name='Jefe de Área')
                instance.groups.add(grupo)
                
                # ASIGNAR PERMISOS JSON PARA JEFE DE ÁREA
                instance.permisos_personalizados = {
                    'puede_crear_solicitudes': True,
                    'validador_finanzas': False,
                    'validador_abastecimiento': True,
                    'puede_crear_usuarios': True,
                    'puede_ver_solicitudes_area': True,
                    'limite_aprobacion': 50000
                }
                instance.save(update_fields=['permisos_personalizados'])
                
                logger.info(f"✅ [SIGNAL] Rol 'Jefe de Área' asignado a {instance.email}")
            
            else:
                # Usuario sin área → Empleado básico
                grupo = Group.objects.get(name='Empleado')
                instance.groups.add(grupo)
                
                # ASIGNAR PERMISOS JSON PARA EMPLEADO
                instance.permisos_personalizados = {
                    'puede_crear_solicitudes': True,
                    'validador_finanzas': False,
                    'validador_abastecimiento': False,
                    'puede_crear_usuarios': False,
                    'puede_ver_solicitudes_propias': True,
                    'limite_aprobacion': 5000
                }
                instance.save(update_fields=['permisos_personalizados'])
                
                logger.info(f"✅ [SIGNAL] Rol 'Empleado' asignado a {instance.email}")
        
        except Group.DoesNotExist as e:
            logger.error(f"❌ [SIGNAL] Error: Grupo no encontrado - {str(e)}")
            logger.warning("⚠️ Ejecuta: python manage.py bootstrap_roles")


@receiver(post_save, sender=Usuario) 
def asignar_permisos_lambda_signal(sender, instance, created, **kwargs):
    """
    Signal especial para usuarios Lambda con permisos completos
    """
    if created and not instance.empresa:  # Usuario Lambda (sin empresa)
        # Asignar rol Admin Lambda
        try:
            grupo = Group.objects.get(name='Admin Lambda')
            instance.groups.add(grupo)
            
            # PERMISOS COMPLETOS PARA LAMBDA
            instance.permisos_personalizados = {
                'puede_crear_solicitudes': True,
                'validador_finanzas': True,
                'validador_abastecimiento': True,
                'puede_crear_usuarios': True,
                'puede_ver_todas_solicitudes': True,
                'puede_gestionar_pagos': True,
                'puede_facturar': True,
                'limite_aprobacion': 999999999,  # Sin límite
                'es_usuario_lambda': True
            }
            instance.save(update_fields=['permisos_personalizados'])
            
            logger.info(f"✅ [SIGNAL] Permisos Lambda completos asignados a {instance.email}")
            
        except Group.DoesNotExist:
            logger.error("❌ [SIGNAL] Grupo 'Admin Lambda' no existe")
            logger.warning("⚠️ Ejecuta: python manage.py bootstrap_roles")