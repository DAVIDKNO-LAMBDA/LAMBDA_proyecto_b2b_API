from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pedido
import logging

logger = logging.getLogger(__name__)

# Signals para Pedidos - por ahora vacío, se puede expandir después
# Los signals principales están en Usuarios