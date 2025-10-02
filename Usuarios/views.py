from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Usuario, EmpleadoAudit, ActivationToken
from .serializers import UsuarioSerializer, EmpleadoCreateSerializer, EmpleadoUpdateSerializer, ActivacionSerializer
#from Base.utils import enviar_correo_activacion

class ActivateAccount(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ActivacionSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UsuarioSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmpleadosList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Usuario.objects.filter(empresa=request.user.empresa).exclude(pk=request.user.pk)
        estado = request.query_params.get("estado")
        area = request.query_params.get("area")
        if estado:
            qs = qs.filter(estado=estado.lower() in ["true","1","activo"])
        if area:
            qs = qs.filter(area__iexact=area)
        qs = qs.order_by(request.query_params.get("ordering","first_name"))
        return Response(UsuarioSerializer(qs, many=True).data)

class EmpleadoCreate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmpleadoCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            empleado = serializer.save()
            token = ActivationToken.objects.filter(user=empleado).last()
            #enviar_correo_activacion(empleado.email, token.token)
            return Response(UsuarioSerializer(empleado).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmpleadoUpdate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        empleado = get_object_or_404(Usuario, pk=pk, empresa=request.user.empresa)
        serializer = EmpleadoUpdateSerializer(empleado, data=request.data, partial=True)
        if serializer.is_valid():
            empleado = serializer.save()
            EmpleadoAudit.objects.create(empleado=empleado, modificado_por=request.user, comentario="Actualización")
            return Response(UsuarioSerializer(empleado).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
