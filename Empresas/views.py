from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Empresa, Area
from .serializers import EmpresaSerializer, AreaSerializer

class EmpresaListCreate(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        empresas = Empresa.objects.all()
        serializer = EmpresaSerializer(empresas, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = EmpresaSerializer(data=request.data)
        if serializer.is_valid():
            empresa = serializer.save()
            return Response(EmpresaSerializer(empresa).data, status=status.HTTP_201_CREATED)
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


class AreaListCreate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, empresa_id):
        areas = Area.objects.filter(empresa_id=empresa_id)
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)

    def post(self, request, empresa_id):
        data = request.data.copy()
        data["empresa"] = empresa_id
        serializer = AreaSerializer(data=data)
        if serializer.is_valid():
            area = serializer.save()
            return Response(AreaSerializer(area).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
