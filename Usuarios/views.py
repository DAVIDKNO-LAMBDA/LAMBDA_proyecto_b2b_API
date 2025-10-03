from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Usuario
from .serializers import UsuarioSerializer, UsuarioCreateSerializer, UsuarioUpdateSerializer
from .decorators import requiere_permiso

class UsuarioList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        usuarios = Usuario.objects.filter(empresa=request.user.empresa)
        serializer = UsuarioSerializer(usuarios, many=True)
        return Response(serializer.data)


class UsuarioCreate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @requiere_permiso("Usuarios.es_admin_empresa")
    def post(self, request):
        serializer = UsuarioCreateSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsuarioUpdate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @requiere_permiso("Usuarios.es_admin_empresa")
    def put(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk, empresa=request.user.empresa)
        serializer = UsuarioUpdateSerializer(usuario, data=request.data, partial=True)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response(UsuarioSerializer(usuario).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
