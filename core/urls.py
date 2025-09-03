# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet, CarteraViewSet, PrestamoViewSet, PagoViewSet
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenVerifyView)

router = DefaultRouter()
router.register('carteras', CarteraViewSet, basename='carteras')
router.register('clientes', ClienteViewSet, basename='clientes')
router.register('prestamos', PrestamoViewSet, basename='prestamos')
router.register('pagos',    PagoViewSet,    basename='pagos')

urlpatterns = [
    path('/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

urlpatterns = [path('', include(router.urls))]
