"""
URLs para la API del dashboard.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AuthViewSet, ProjectViewSet, MaterialViewSet, ApprovalViewSet,
    PlatformSpecViewSet, DashboardStatsView, PlatformSpecsListView
)

# Router para ViewSets
router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'materials', MaterialViewSet, basename='materials')
router.register(r'approvals', ApprovalViewSet, basename='approvals')
router.register(r'platform-specs', PlatformSpecViewSet, basename='platform-specs')

urlpatterns = [
    # URLs del router (ViewSets)
    path('', include(router.urls)),
    
    # JWT Token refresh
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # URLs específicas para estadísticas
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('platform-specs/list/', PlatformSpecsListView.as_view(), name='platform-specs-list'),
]
