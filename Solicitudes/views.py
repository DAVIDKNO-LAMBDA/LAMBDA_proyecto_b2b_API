from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from Solicitudes.models import Solicitud, ProductoSolicitud, HistorialAprobacion
from Solicitudes.serializers import (
    SolicitudSerializer, SolicitudDetalleSerializer, CrearSolicitudSerializer
)
from Usuarios.decorators import permiso_requerido


# =========================
# HU10: Crear Solicitud
# =========================
class CrearSolicitudView(generics.CreateAPIView):
    serializer_class = CrearSolicitudSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        solicitud = serializer.save()
        data = SolicitudDetalleSerializer(solicitud).data
        return Response(data, status=status.HTTP_201_CREATED)


# =========================
# HU11: Listar Solicitudes
# =========================
class ListarSolicitudesView(generics.ListAPIView):
    serializer_class = SolicitudSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Solicitud.objects.filter(empresa=self.request.user.empresa).select_related("solicitante", "empresa")
        # Filtros opcionales: estado, solicitante, fecha (YYYY-MM-DD)
        estado = self.request.query_params.get("estado")
        solicitante_id = self.request.query_params.get("solicitante")
        fecha_desde = self.request.query_params.get("desde")
        fecha_hasta = self.request.query_params.get("hasta")

        if estado:
            qs = qs.filter(estado=estado)
        if solicitante_id:
            qs = qs.filter(solicitante_id=solicitante_id)
        if fecha_desde:
            qs = qs.filter(creado__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(creado__date__lte=fecha_hasta)

        return qs


class DetalleSolicitudView(generics.RetrieveAPIView):
    serializer_class = SolicitudDetalleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Solicitud.objects.filter(empresa=self.request.user.empresa)


# =========================================
# HU12: Validación de Abastecimiento (cliente)
# =========================================
class AprobarAbastecimientoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @permiso_requerido("Usuarios.valida_logistica")
    @transaction.atomic
    def post(self, request, pk):
        """
        Body esperado:
        {
          "accion": "aprobar" | "rechazar" | "modificar",
          "comentario": "texto opcional",
          "productos": [
             {"id": 10, "cantidad": 8},  // solo si accion == "modificar"
          ]
        }
        """
        solicitud = get_object_or_404(Solicitud, pk=pk, empresa=request.user.empresa)

        if solicitud.estado != "pendiente_abastecimiento":
            return Response({"detail": "La solicitud no está pendiente de abastecimiento."},
                            status=status.HTTP_400_BAD_REQUEST)

        accion = request.data.get("accion")
        comentario = request.data.get("comentario", "")

        if accion not in ["aprobar", "rechazar", "modificar"]:
            return Response({"detail": "Acción inválida."}, status=status.HTTP_400_BAD_REQUEST)

        if accion == "rechazar":
            solicitud.estado = "rechazada"
            solicitud.save()
            HistorialAprobacion.objects.create(
                solicitud=solicitud,
                usuario=request.user,
                estado_aprobacion="rechazado_abastecimiento",
                comentario=comentario or "Rechazado por abastecimiento"
            )
            return Response({"detail": "Solicitud rechazada por abastecimiento."}, status=status.HTTP_200_OK)

        if accion == "modificar":
            items = request.data.get("productos", [])
            if not isinstance(items, list) or not items:
                return Response({"detail": "Debes enviar 'productos' para modificar cantidades."},
                                status=status.HTTP_400_BAD_REQUEST)

            # modificar cantidades
            for item in items:
                prod_id = item.get("id")
                cantidad = item.get("cantidad")
                if not prod_id or cantidad is None:
                    return Response({"detail": "Cada producto necesita 'id' y 'cantidad'."},
                                    status=status.HTTP_400_BAD_REQUEST)
                try:
                    cantidad = int(cantidad)
                except Exception:
                    return Response({"detail": "Cantidad inválida."}, status=status.HTTP_400_BAD_REQUEST)
                if cantidad <= 0:
                    return Response({"detail": "La cantidad debe ser mayor a 0."}, status=status.HTTP_400_BAD_REQUEST)

                prod = get_object_or_404(ProductoSolicitud, id=prod_id, solicitud=solicitud)
                prod.cantidad = cantidad
                prod.save()

            HistorialAprobacion.objects.create(
                solicitud=solicitud,
                usuario=request.user,
                estado_aprobacion="modificado_abastecimiento",
                comentario=comentario or "Cantidades ajustadas por abastecimiento"
            )
            # Después de modificar, sigue pendiente de abastecimiento hasta que se apruebe explícitamente
            return Response({"detail": "Cantidades modificadas. Aún debes 'aprobar'."}, status=status.HTTP_200_OK)

        # aprobar
        solicitud.estado = "pendiente_finanzas"
        solicitud.save()
        HistorialAprobacion.objects.create(
            solicitud=solicitud,
            usuario=request.user,
            estado_aprobacion="aprobado_abastecimiento",
            comentario=comentario or "Aprobado por abastecimiento"
        )
        return Response({"detail": "Solicitud aprobada por abastecimiento y enviada a finanzas."}, status=status.HTTP_200_OK)


# ======================================
# HU13: Validación Financiera (cliente)
# ======================================
class AprobarFinanzasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @permiso_requerido("Usuarios.valida_financiero")
    @transaction.atomic
    def post(self, request, pk):
        """
        Body esperado:
        {
          "accion": "aprobar" | "rechazar",
          "comentario": "texto opcional"
        }
        """
        solicitud = get_object_or_404(Solicitud, pk=pk, empresa=request.user.empresa)

        if solicitud.estado != "pendiente_finanzas":
            return Response({"detail": "La solicitud no está pendiente de finanzas."},
                            status=status.HTTP_400_BAD_REQUEST)

        accion = request.data.get("accion")
        comentario = request.data.get("comentario", "")

        if accion not in ["aprobar", "rechazar"]:
            return Response({"detail": "Acción inválida."}, status=status.HTTP_400_BAD_REQUEST)

        if accion == "rechazar":
            solicitud.estado = "rechazada"
            solicitud.save()
            HistorialAprobacion.objects.create(
                solicitud=solicitud,
                usuario=request.user,
                estado_aprobacion="rechazado_finanzas",
                comentario=comentario or "Rechazado por finanzas"
            )
            return Response({"detail": "Solicitud rechazada por finanzas."}, status=status.HTTP_200_OK)

        # aprobar
        solicitud.estado = "aprobada"
        solicitud.save()
        HistorialAprobacion.objects.create(
            solicitud=solicitud,
            usuario=request.user,
            estado_aprobacion="aprobado_finanzas",
            comentario=comentario or "Aprobado por finanzas (lista para generar pedido a Lambda)"
        )
        # 🔜 FUTURO (HU14): aquí podemos emitir una señal para crear el Pedido externo a Lambda.
        return Response({"detail": "Solicitud aprobada por finanzas. Lista para generar pedido a Lambda."},
                        status=status.HTTP_200_OK)
