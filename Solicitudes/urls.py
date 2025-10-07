from django.urls import path
from Solicitudes.views import (
    CrearSolicitudView, ListarSolicitudesView, DetalleSolicitudView,
    AprobarAbastecimientoView, AprobarFinanzasView
)

urlpatterns = [
    path("solicitudes/crear/", CrearSolicitudView.as_view(), name="crear_solicitud"),
    path("solicitudes/", ListarSolicitudesView.as_view(), name="listar_solicitudes"),
    path("solicitudes/<int:pk>/", DetalleSolicitudView.as_view(), name="detalle_solicitud"),
    path("solicitudes/<int:pk>/aprobar/abastecimiento/", AprobarAbastecimientoView.as_view(), name="aprobar_abastecimiento"),
    path("solicitudes/<int:pk>/aprobar/finanzas/", AprobarFinanzasView.as_view(), name="aprobar_finanzas"),
]



