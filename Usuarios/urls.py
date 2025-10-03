from django.urls import path
from .views import UsuarioList, UsuarioCreate, UsuarioUpdate

urlpatterns = [
    path("usuarios/", UsuarioList.as_view(), name="usuarios-list"),
    path("usuarios/create/", UsuarioCreate.as_view(), name="usuarios-create"),
    path("usuarios/update/<int:pk>/", UsuarioUpdate.as_view(), name="usuarios-update"),
]
