from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def enviar_correo_html(destinatario, asunto, template_name, contexto):
    """
    Función genérica para enviar correos con template HTML
    
    Args:
        destinatario (str): Email del destinatario
        asunto (str): Asunto del correo
        template_name (str): Ruta del template HTML relativa a TEMPLATES/DIRS
        contexto (dict): Diccionario con variables para el template
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        # Renderizar template HTML
        html_content = render_to_string(template_name, contexto)
        
        # Extraer texto plano del HTML (fallback)
        text_content = strip_tags(html_content)
        
        # Crear mensaje
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[destinatario]
        )
        
        # Adjuntar versión HTML
        email.attach_alternative(html_content, "text/html")
        
        # Enviar
        email.send(fail_silently=False)
        
        logger.info(f"✅ Correo enviado exitosamente a {destinatario}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error enviando correo a {destinatario}: {str(e)}")
        return False


def enviar_correo_activacion_usuario(usuario, creador=None):
    """
    Envía correo de activación a un usuario de empresa
    
    Args:
        usuario (Usuario): Instancia del usuario
        creador (Usuario): Usuario que creó la cuenta (opcional)
    
    Returns:
        bool: True si se envió correctamente
    """
    if not usuario.empresa or not usuario.token_activacion:
        logger.warning(f"No se puede enviar correo de activación a {usuario.email}")
        return False
    
    # Construir URL de activación
    base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    url_activacion = f"{base_url}/activar/{usuario.token_activacion}"
    
    # Determinar quién creó el usuario
    nombre_creador = "El administrador"
    if creador:
        nombre_creador = creador.get_full_name() or creador.email
    
    # Contexto para el template
    contexto = {
        'nombre_usuario': usuario.get_full_name() or usuario.email,
        'email': usuario.email,
        'empresa': usuario.empresa.nombre,
        'area': usuario.area.nombre if usuario.area else 'Sin área asignada',
        'cargo': usuario.cargo or 'Sin cargo definido',
        'creador': nombre_creador,
        'url_activacion': url_activacion,
        'token': usuario.token_activacion,
    }
    
    # Enviar correo usando la ruta correcta del template
    return enviar_correo_html(
        destinatario=usuario.email,
        asunto=f"Activación de cuenta - {usuario.empresa.nombre}",
        template_name='Usuarios/Emails/activacion.html',  # Ruta relativa a Templates/
        contexto=contexto
    )


def enviar_correo_bienvenida_lambda(usuario, password_temporal):
    """
    Envía correo de bienvenida a usuarios internos de Lambda con contraseña temporal
    
    Args:
        usuario (Usuario): Instancia del usuario de Lambda
        password_temporal (str): Contraseña temporal generada
    
    Returns:
        bool: True si se envió correctamente
    """
    if usuario.empresa:
        logger.warning(f"Este método es solo para usuarios de Lambda")
        return False
    
    contexto = {
        'nombre_usuario': usuario.get_full_name() or usuario.email,
        'email': usuario.email,
        'password_temporal': password_temporal,
        'url_login': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') + '/login',
    }
    
    return enviar_correo_html(
        destinatario=usuario.email,
        asunto="Bienvenido a Lambda Commerce Solutions",
        template_name='Usuarios/Emails/bienvenida_lambda.html',
        contexto=contexto
    )


def enviar_correo_recuperacion_password(usuario, token_recuperacion):
    """
    Envía correo de recuperación de contraseña
    
    Args:
        usuario (Usuario): Instancia del usuario
        token_recuperacion (str): Token para recuperar contraseña
    
    Returns:
        bool: True si se envió correctamente
    """
    base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    url_recuperacion = f"{base_url}/recuperar-password/{token_recuperacion}"
    
    contexto = {
        'nombre_usuario': usuario.get_full_name() or usuario.email,
        'url_recuperacion': url_recuperacion,
        'token': token_recuperacion,
    }
    
    return enviar_correo_html(
        destinatario=usuario.email,
        asunto="Recuperación de contraseña - Lambda B2B",
        template_name='Usuarios/Emails/recuperacion_password.html',
        contexto=contexto
    )
