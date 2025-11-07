# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet, CarteraViewSet, PrestamoViewSet, PagoViewSet, InteresViewSet, PrestamoViewSet, CuotaViewSet, PagoViewSet, dashboard_view, actualizar_estados_view, secure_media_proxy, test_auth, debug_frontend
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenVerifyView)

router = DefaultRouter()
router.register('carteras', CarteraViewSet, basename='carteras')
router.register('clientes', ClienteViewSet, basename='clientes')
router.register('intereses', InteresViewSet, basename='interes')
router.register('cuotas', CuotaViewSet, basename='cuota')
router.register('prestamos', PrestamoViewSet, basename='prestamos')
router.register('pagos',    PagoViewSet,    basename='pagos')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('actualizar-estados/', actualizar_estados_view, name='actualizar-estados'),
    path('secure-media/<path:path>', secure_media_proxy, name='secure-media'),
    path('test-auth/', test_auth, name='test-auth'),
    path('debug-frontend/', debug_frontend, name='debug-frontend'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
