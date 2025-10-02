from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Empresa
from .serializers import EmpresaSerializer
from Usuarios.models import Usuario, ActivationToken
#from Base.utils import enviar_correo_activacion

class EmpresaList(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        empresas = Empresa.objects.filter(estado=True)
        nombre = request.query_params.get("nombre")
        nit = request.query_params.get("nit")
        estado = request.query_params.get("estado")

        if nombre:
            empresas = empresas.filter(nombre__icontains=nombre)
        if nit:
            empresas = empresas.filter(nit__icontains=nit)
        if estado:
            empresas = empresas.filter(estado=estado.lower() in ["true","1","activo"])

        serializer = EmpresaSerializer(empresas, many=True)
        return Response(serializer.data)

class EmpresaCreate(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = EmpresaSerializer(data=request.data)
        if serializer.is_valid():
            empresa = serializer.save()

            usuario_inicial = Usuario.objects.create(
                username=empresa.nit,
                email=empresa.correo_contacto,
                empresa=empresa,
                rol="admin_empresa",
                estado=False
            )
            usuario_inicial.set_unusable_password()
            usuario_inicial.save()

            token = ActivationToken.create_for_user(usuario_inicial)
            #enviar_correo_activacion(empresa.correo_contacto, token.token)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmpresaUpdate(APIView):
    permission_classes = [permissions.IsAdminUser]

    def put(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        serializer = EmpresaSerializer(empresa, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
