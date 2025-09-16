"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import get_user_model
from core.models import CarteraMiembro
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenVerifyView)
from rest_framework.decorators import api_view, permission_classes
from core.views import me_view

User = get_user_model()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def whoami(request):
    user = request.user
    grupos = list(user.groups.values_list("name", flat=True))
    # asignaciones por cartera
    asignaciones = list(
        CarteraMiembro.objects.filter(usuario=user)
        .values("cartera_id", "cartera__nombre", "rol")
    )
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "groups": grupos,                   # p.ej. ["admin"] si lo usas
        "carteras": [
            {"id": str(a["cartera_id"]), "nombre": a["cartera__nombre"], "rol": a["rol"]}
            for a in asignaciones
        ],
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('api/token/refresh/', TokenObtainPairView.as_view(), name="token_refresh"),
    path("api/me/", me_view, name="me"),  
    
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
