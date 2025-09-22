"""
Vistas de la API para el sistema de gestión de materiales.
"""

from rest_framework import status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.http import Http404
import logging

from .models import (
    User, Project, Material, MaterialVersion, Approval, 
    PlatformSpec, DriveLink, AuditLog
)
from .serializers import (
    UserRegistrationSerializer, UserSerializer, ProjectSerializer,
    MaterialSerializer, MaterialUploadSerializer, MaterialVersionSerializer,
    ApprovalSerializer, DriveLinkSerializer, AuditLogSerializer,
    DashboardStatsSerializer, PlatformSpecsListSerializer, LoginSerializer,
    MaterialStatusUpdateSerializer, MaterialRollbackSerializer
)
from .services import MaterialService, ImageValidationError, AuditService
from .constants import UserRole, MaterialStatus, Platform, ProjectStatus

logger = logging.getLogger(__name__)

class AuthViewSet(ModelViewSet):
    """ViewSet para autenticación y gestión de usuarios."""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegistrationSerializer
        elif self.action == 'login':
            return LoginSerializer
        return UserSerializer
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """Registro de nuevos usuarios."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Log de auditoría
            AuditService.log_action(
                action='create',
                actor=user,
                entity_type='User',
                entity_id=user.id,
                payload={'role': user.role},
                request=request
            )
            
            return Response({
                'message': 'Usuario registrado exitosamente',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Login de usuarios con JWT."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            # Log de auditoría
            AuditService.log_action(
                action='login',
                actor=user,
                entity_type='User',
                entity_id=user.id,
                request=request
            )
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Obtener información del usuario autenticado."""
        return Response(UserSerializer(request.user).data)

class ProjectViewSet(ModelViewSet):
    """ViewSet para gestión de proyectos."""
    
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'company', 'created_by']
    search_fields = ['name', 'app_name', 'company', 'description']
    ordering_fields = ['created_at', 'updated_at', 'deadline']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrar proyectos según el rol del usuario."""
        user = self.request.user
        
        if user.is_admin:
            return Project.objects.all()
        elif user.is_reviewer:
            return Project.objects.filter(
                Q(assigned_reviewers=user) | Q(created_by=user)
            ).distinct()
        else:  # Cliente
            return Project.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        """Asignar el usuario actual como creador del proyecto."""
        serializer.save(created_by=self.request.user)
        
        # Log de auditoría
        AuditService.log_action(
            action='create',
            actor=self.request.user,
            entity_type='Project',
            entity_id=serializer.instance.id,
            payload={
                'project_name': serializer.instance.name,
                'company': serializer.instance.company,
                'app_name': serializer.instance.app_name
            },
            request=self.request
        )
    
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        """Obtener materiales de un proyecto."""
        project = self.get_object()
        materials = project.materials.all()
        
        # Aplicar filtros
        platform = request.query_params.get('platform')
        status_filter = request.query_params.get('status')
        
        if platform:
            materials = materials.filter(platform=platform)
        if status_filter:
            materials = materials.filter(status=status_filter)
        
        serializer = MaterialSerializer(materials, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas de un proyecto."""
        project = self.get_object()
        
        total_materials = project.materials.count()
        approved_materials = project.materials.filter(status=MaterialStatus.APPROVED).count()
        pending_materials = project.materials.filter(status=MaterialStatus.PENDING).count()
        needs_correction = project.materials.filter(status=MaterialStatus.NEEDS_CORRECTION).count()
        
        completion_percentage = project.completion_percentage
        is_overdue = project.is_overdue
        
        return Response({
            'total_materials': total_materials,
            'approved_materials': approved_materials,
            'pending_materials': pending_materials,
            'needs_correction': needs_correction,
            'completion_percentage': completion_percentage,
            'is_overdue': is_overdue,
            'status': project.status
        })

class MaterialViewSet(ModelViewSet):
    """ViewSet para gestión de materiales."""
    
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'platform', 'material_type', 'project']
    search_fields = ['file_name', 'asset_key', 'project__name', 'project__app_name']
    ordering_fields = ['created_at', 'updated_at', 'file_size']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrar materiales según el rol del usuario."""
        user = self.request.user
        
        if user.is_admin:
            return Material.objects.all()
        elif user.is_reviewer:
            return Material.objects.filter(
                Q(project__assigned_reviewers=user) | Q(uploaded_by=user)
            ).distinct()
        else:  # Cliente
            return Material.objects.filter(uploaded_by=user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Subir un nuevo material con validación automática."""
        serializer = MaterialUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Obtener datos validados
            project = serializer.validated_data['project']
            platform = serializer.validated_data['platform']
            asset_key = serializer.validated_data['asset_key']
            file = serializer.validated_data['file']
            comments = serializer.validated_data.get('comments', '')
            
            # Leer contenido del archivo
            file_content = file.read()
            
            # Crear material usando el servicio
            material_service = MaterialService()
            material = material_service.create_material(
                project=project,
                platform=platform,
                asset_key=asset_key,
                file_content=file_content,
                file_name=file.name,
                uploaded_by=request.user,
                request=request
            )
            
            # Asignar comentarios si los hay
            if comments:
                material.comments = comments
                material.save()
            
            # Crear aprobaciones automáticas para revisores asignados
            if project.assigned_reviewers.exists():
                for reviewer in project.assigned_reviewers.all():
                    Approval.objects.create(
                        material=material,
                        reviewer=reviewer,
                        status=MaterialStatus.PENDING
                    )
            
            return Response(
                MaterialSerializer(material).data,
                status=status.HTTP_201_CREATED
            )
            
        except ImageValidationError as e:
            logger.warning(f"Validación fallida para {file.name}: {str(e)}")
            return Response({
                'error': 'Archivo no válido',
                'details': str(e),
                'file_name': file.name
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error subiendo archivo {file.name}: {str(e)}")
            return Response({
                'error': 'Error interno del servidor',
                'details': 'No se pudo procesar el archivo'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Actualizar estado de un material."""
        material = self.get_object()
        serializer = MaterialStatusUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        new_status = serializer.validated_data['status']
        comments = serializer.validated_data.get('comments', '')
        
        # Verificar permisos para cambio de estado
        if not self._can_change_status(material, new_status, request.user):
            return Response({
                'error': 'No tienes permisos para realizar esta acción'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Actualizar estado usando el servicio
        material_service = MaterialService()
        material_service.update_material_status(
            material=material,
            new_status=new_status,
            user=request.user,
            comments=comments,
            request=request
        )
        
        return Response(MaterialSerializer(material).data)
    
    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """Hacer rollback a una versión anterior."""
        material = self.get_object()
        serializer = MaterialRollbackSerializer(
            data=request.data,
            context={'material_id': material.id}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        version_id = serializer.validated_data['version_id']
        
        try:
            version = MaterialVersion.objects.get(
                id=version_id,
                material=material
            )
            
            # Actualizar material con datos de la versión
            material.file_name = version.file_name
            material.file_size = version.file_size
            material.file_hash = version.file_hash
            material.mime_type = version.mime_type
            material.width = version.width
            material.height = version.height
            material.has_transparency = version.has_transparency
            material.storage_url = version.storage_url
            material.status = MaterialStatus.PENDING  # Volver a pendiente
            material.save()
            
            # Log de auditoría
            AuditService.log_action(
                action='update',
                actor=request.user,
                entity_type='Material',
                entity_id=material.id,
                payload={
                    'action': 'rollback',
                    'version_id': version_id,
                    'version_number': version.version_number
                },
                request=request
            )
            
            return Response(MaterialSerializer(material).data)
            
        except MaterialVersion.DoesNotExist:
            return Response({
                'error': 'Versión no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Obtener versiones de un material."""
        material = self.get_object()
        versions = material.versions.all()
        serializer = MaterialVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    def _can_change_status(self, material, new_status, user):
        """Verificar si el usuario puede cambiar el estado del material."""
        if user.is_admin:
            return True
        
        if user.is_reviewer:
            # Los revisores pueden aprobar/rechazar materiales asignados
            if new_status in [MaterialStatus.APPROVED, MaterialStatus.NEEDS_CORRECTION]:
                return material.project.assigned_reviewers.filter(id=user.id).exists()
        
        if user.is_client:
            # Los clientes solo pueden subir materiales (estado pending)
            return new_status == MaterialStatus.PENDING and material.uploaded_by == user
        
        return False

class ApprovalViewSet(ModelViewSet):
    """ViewSet para gestión de aprobaciones."""
    
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'reviewer', 'material__project']
    search_fields = ['material__file_name', 'material__asset_key', 'reviewer__username']
    ordering_fields = ['created_at', 'updated_at', 'approved_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrar aprobaciones según el rol del usuario."""
        user = self.request.user
        
        if user.is_admin:
            return Approval.objects.all()
        elif user.is_reviewer:
            return Approval.objects.filter(reviewer=user)
        else:  # Cliente
            return Approval.objects.filter(material__uploaded_by=user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Aprobar un material."""
        approval = self.get_object()
        
        if approval.reviewer != request.user and not request.user.is_admin:
            return Response({
                'error': 'No tienes permisos para aprobar este material'
            }, status=status.HTTP_403_FORBIDDEN)
        
        comments = request.data.get('comments', '')
        approval.approve(comments)
        
        return Response(ApprovalSerializer(approval).data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rechazar un material."""
        approval = self.get_object()
        
        if approval.reviewer != request.user and not request.user.is_admin:
            return Response({
                'error': 'No tienes permisos para rechazar este material'
            }, status=status.HTTP_403_FORBIDDEN)
        
        comments = request.data.get('comments', '')
        approval.reject(comments)
        
        return Response(ApprovalSerializer(approval).data)

class PlatformSpecViewSet(ModelViewSet):
    """ViewSet para gestión de especificaciones de plataforma."""
    
    queryset = PlatformSpec.objects.all()
    serializer_class = PlatformSpecSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['platform', 'is_active']
    search_fields = ['platform', 'asset_key']
    
    def get_queryset(self):
        """Solo administradores pueden gestionar especificaciones."""
        if self.request.user.is_admin:
            return PlatformSpec.objects.all()
        return PlatformSpec.objects.filter(is_active=True)

class DashboardStatsView(APIView):
    """Vista para estadísticas del dashboard."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener estadísticas generales del dashboard."""
        user = request.user
        
        # Filtrar datos según el rol del usuario
        if user.is_admin:
            projects = Project.objects.all()
            materials = Material.objects.all()
        elif user.is_reviewer:
            projects = Project.objects.filter(assigned_reviewers=user)
            materials = Material.objects.filter(project__assigned_reviewers=user)
        else:  # Cliente
            projects = Project.objects.filter(created_by=user)
            materials = Material.objects.filter(uploaded_by=user)
        
        # Calcular estadísticas
        total_projects = projects.count()
        total_materials = materials.count()
        pending_materials = materials.filter(status=MaterialStatus.PENDING).count()
        approved_materials = materials.filter(status=MaterialStatus.APPROVED).count()
        overdue_projects = projects.filter(
            deadline__lt=timezone.now(),
            status__in=[ProjectStatus.DRAFT, ProjectStatus.IN_PROGRESS]
        ).count()
        
        # Tiempo promedio de aprobación
        approved_approvals = Approval.objects.filter(
            status=MaterialStatus.APPROVED,
            approved_at__isnull=False
        )
        if approved_approvals.exists():
            avg_approval_time = approved_approvals.aggregate(
                avg_time=Avg('approved_at' - 'created_at')
            )['avg_time']
            avg_approval_time_hours = avg_approval_time.total_seconds() / 3600 if avg_approval_time else 0
        else:
            avg_approval_time_hours = 0
        
        # Materiales por estado
        materials_by_status = {}
        for status_choice in MaterialStatus.CHOICES:
            status_key = status_choice[0]
            count = materials.filter(status=status_key).count()
            materials_by_status[status_key] = count
        
        # Materiales por plataforma
        materials_by_platform = {}
        for platform_choice in Platform.CHOICES:
            platform_key = platform_choice[0]
            count = materials.filter(platform=platform_key).count()
            materials_by_platform[platform_key] = count
        
        # Actividades recientes (últimos 10 logs)
        recent_logs = AuditLog.objects.filter(actor=user).order_by('-created_at')[:10]
        recent_activities = []
        for log in recent_logs:
            recent_activities.append({
                'action': log.get_action_display(),
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'created_at': log.created_at,
                'payload': log.payload
            })
        
        stats_data = {
            'total_projects': total_projects,
            'total_materials': total_materials,
            'pending_materials': pending_materials,
            'approved_materials': approved_materials,
            'overdue_projects': overdue_projects,
            'avg_approval_time_hours': round(avg_approval_time_hours, 2),
            'materials_by_status': materials_by_status,
            'materials_by_platform': materials_by_platform,
            'recent_activities': recent_activities
        }
        
        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data)

class PlatformSpecsListView(APIView):
    """Vista para obtener todas las especificaciones de plataforma."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener lista de especificaciones por plataforma."""
        from .constants import PLATFORM_SPECS
        
        specs_list = []
        for platform_key, platform_display in Platform.CHOICES:
            platform_specs = PLATFORM_SPECS.get(platform_key, {})
            specs_list.append({
                'platform': platform_key,
                'platform_display': platform_display,
                'assets': platform_specs
            })
        
        serializer = PlatformSpecsListSerializer(specs_list, many=True)
        return Response(serializer.data)